"""Tile tests (Stage 2): TILE_ROWS PEs share one broadcast x, each with its own weight. Bit-exact against raw_acc.

Ports: clk, in_valid, clr, x (INT8, broadcast), w (one INT4 weight per row, row r at bits [4r+3:4r]),
acc (one accumulator per row, row r at bits [ACC_W*r+ACC_W-1 : ACC_W*r]), done (high after the Kth valid term).
TILE_ROWS and K come from the environment, set by `make test-tile`, so the same tests cover any tile size.
"""
import os
import random
from pathlib import Path

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from golden import raw_acc

TILE_ROWS = int(os.environ.get("TILE_ROWS", "4"))
K = int(os.environ.get("TILE_K", "576"))  # 576 is up_proj's K in Stage 1
ACC_W = 21
W_BITS = 4
NPZ_PATH = Path(__file__).resolve().parents[1] / "export" / "out" / "layer15_up_proj.npz"
RANDOM_SEED = 3  # fixed so a failure reproduces
RANDOM_RUNS = 20
GAP_MAX = 3  # up to 3 idle cycles between accepted terms
GAP_RUNS = 5  # row sets in a row, each restarted with clr, each with its own random gaps
REAL_LAYER_SPLITS = ("x_cal_int", "x_test_int")  # calibration vectors and held-out test vectors from the export
REAL_LAYER_ROW_STEP = 64  # every 64th of the 1,536 rows: 24 rows, 6 tile runs of 4
CLOCK_PERIOD_NS = 10


def pack_weights(w_column):
    """Pack one INT4 weight per row into the flat w bus, row r at bits [4r+3:4r]."""
    bus = 0
    for r, w in enumerate(w_column):
        bus |= (w & 0xF) << (W_BITS * r)  # mask to 4 bits, two's complement
    return bus


def unpack_accs(bus):
    """Split the flat acc bus into signed per-row accumulators."""
    mask = (1 << ACC_W) - 1
    accs = []
    for r in range(TILE_ROWS):
        field = (bus >> (ACC_W * r)) & mask
        accs.append(field - (1 << ACC_W) if field >> (ACC_W - 1) else field)  # sign-extend the field
    return accs


async def start_clock(dut):
    """Start the clock and drive all inputs to zero before the first term."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, units="ns").start())
    dut.in_valid.value = 0
    dut.clr.value = 0
    dut.x.value = 0
    dut.w.value = 0


async def send_term(dut, x, w_column, clr):
    """Drive one valid term on the falling edge, so it is sampled on the next rising edge."""
    await FallingEdge(dut.clk)
    dut.in_valid.value = 1
    dut.clr.value = int(clr)
    dut.x.value = x & 0xFF
    dut.w.value = pack_weights(w_column)
    await RisingEdge(dut.clk)


async def idle_cycle(dut):
    """One cycle with in_valid low, so acc and done must not move (except done clearing)."""
    await FallingEdge(dut.clk)
    dut.in_valid.value = 0
    dut.clr.value = 0
    await RisingEdge(dut.clk)


async def read_tile(dut):
    """Read acc and done a hair after the edge, so the flops have settled."""
    await Timer(1, units="ns")
    return unpack_accs(int(dut.acc.value)), int(dut.done.value)


async def run_tile(dut, xs, q_rows):
    """One dot product per row over K terms, clr on term 0. done must be high only after term K-1."""
    accs = None
    for i, x in enumerate(xs):
        w_column = [row[i] for row in q_rows]  # row r's own weight for this term
        await send_term(dut, x, w_column, clr=(i == 0))
        accs, done = await read_tile(dut)
        expected_done = int(i == K - 1)
        assert done == expected_done, f"term {i}: done={done}, expected {expected_done}"
    return accs


@cocotb.test()
async def tile_random(dut):
    """Random weights and activations, bit-exact for every row."""
    await start_clock(dut)
    rng = random.Random(RANDOM_SEED)
    for run in range(RANDOM_RUNS):
        q_rows = [[rng.randint(-8, 7) for _ in range(K)] for _ in range(TILE_ROWS)]
        xs = [rng.randint(-127, 127) for _ in range(K)]
        expected = raw_acc(q_rows, xs)
        got = await run_tile(dut, xs, q_rows)
        assert got == expected, f"random run {run}: expected {expected}, got {got}"


@cocotb.test()
async def gaps_hold_acc_and_done_follows_accepted_terms(dut):
    """Random idle gaps inside each row set, several row sets in a row, each restarted with clr. Bit-exact.

    Covers the memory-side case: the tile must hold acc through gaps, and the clr restart must reset
    both the sum and the term count, so done lands on the Kth accepted term of every row set.
    """
    await start_clock(dut)
    rng = random.Random(RANDOM_SEED + 2)
    for run in range(GAP_RUNS):
        q_rows = [[rng.randint(-8, 7) for _ in range(K)] for _ in range(TILE_ROWS)]
        xs = [rng.randint(-127, 127) for _ in range(K)]
        expected = raw_acc(q_rows, xs)
        got = await run_row_set_with_gaps(dut, xs, q_rows, rng)
        assert got == expected, f"gap run {run}: expected {expected}, got {got}"
        for _ in range(rng.randint(1, GAP_MAX)):  # idle between row sets, then the next one starts with clr
            await gap_cycle(dut, rng)


@cocotb.test()
async def done_pulses_once_and_acc_holds(dut):
    """After done, one idle cycle drops done, and acc stays at its final value."""
    await start_clock(dut)
    q_rows = [[1] * K for _ in range(TILE_ROWS)]
    xs = [1] * K
    final = await run_tile(dut, xs, q_rows)  # the last term raises done
    await idle_cycle(dut)
    accs, done = await read_tile(dut)
    assert done == 0, "done still high one cycle after the last term"
    assert accs == final, f"acc moved while idle: before={final}, after={accs}"


async def gap_cycle(dut, rng):
    """One cycle with in_valid low and random junk on x and w. The tile must ignore all of it."""
    await FallingEdge(dut.clk)
    dut.in_valid.value = 0
    dut.clr.value = 0
    dut.x.value = rng.randint(-128, 127) & 0xFF
    dut.w.value = rng.randint(0, 15)
    await RisingEdge(dut.clk)


async def run_row_set_with_gaps(dut, xs, q_rows, rng):
    """One row set of K accepted terms, with random idle gaps before each term after the first.

    After every gap cycle, acc must not move and done must be low. done must be high exactly
    after the Kth accepted term, however many gap cycles came before it.
    """
    accs = None
    for i, x in enumerate(xs):
        if i > 0:
            for _ in range(rng.randint(0, GAP_MAX)):
                await gap_cycle(dut, rng)
                gap_accs, gap_done = await read_tile(dut)
                assert gap_done == 0, f"term {i}: done high during a gap"
                assert gap_accs == accs, f"term {i}: acc moved during a gap, before={accs}, after={gap_accs}"
        await send_term(dut, x, [row[i] for row in q_rows], clr=(i == 0))
        accs, done = await read_tile(dut)
        assert done == int(i == K - 1), f"term {i}: done={done}, expected {int(i == K - 1)}"
    return accs


def sampled_row_groups(total_rows):
    """Every REAL_LAYER_ROW_STEP-th row, cut into groups of TILE_ROWS. Each group is one tile run."""
    rows = list(range(0, total_rows, REAL_LAYER_ROW_STEP))
    assert len(rows) % TILE_ROWS == 0, f"{len(rows)} sampled rows does not split into tiles of {TILE_ROWS}"
    return [rows[i:i + TILE_ROWS] for i in range(0, len(rows), TILE_ROWS)]


@cocotb.test()
async def tile_real_layer(dut):
    """Sampled rows of q_pc, run on the calibration and held-out vectors, bit-exact. A sample, not all 1,536 rows."""
    await start_clock(dut)
    data = np.load(NPZ_PATH)
    q_all = data["q_pc"].astype(int)
    assert q_all.shape[1] == K, f"layer K is {q_all.shape[1]}, TILE_K is {K}"
    for split in REAL_LAYER_SPLITS:
        x_vectors = data[split].astype(int).tolist()
        x_all = np.array(x_vectors)
        assert -127 <= x_all.min() and x_all.max() <= 127, f"{split}: activation outside [-127, 127] (golden.py contract)"
        for group in sampled_row_groups(q_all.shape[0]):
            q_rows = q_all[group].tolist()
            for v, xs in enumerate(x_vectors):
                expected = raw_acc(q_rows, xs)
                got = await run_tile(dut, xs, q_rows)
                assert got == expected, f"{split} rows {group} vector {v}: expected {expected}, got {got}"


@cocotb.test()
async def missing_clr_accumulates_and_drops_done(dut):
    """Driver contract, documented: a row set whose term 0 has clr=0 is not detected by the tile.

    The tile keeps the previous acc and the previous term count. The bad row set accumulates into the
    old sum, and done does not fire at its Kth term. This test pins that behavior, so it cannot change
    without a test failing. Stage 3 control must keep clr on term 0 and add a sticky error flag.
    """
    await start_clock(dut)
    rng = random.Random(RANDOM_SEED + 1)
    q_a = [[rng.randint(-8, 7) for _ in range(K)] for _ in range(TILE_ROWS)]
    xs_a = [rng.randint(-127, 127) for _ in range(K)]
    q_b = [[rng.randint(-8, 7) for _ in range(K)] for _ in range(TILE_ROWS)]
    xs_b = [rng.randint(-127, 127) for _ in range(K)]

    good = await run_tile(dut, xs_a, q_a)  # good row set first, done fires at its Kth term
    assert good == raw_acc(q_a, xs_a), "good row set is wrong before the bad one even starts"

    for i, x in enumerate(xs_b):  # bad row set: clr stays low on term 0
        await send_term(dut, x, [row[i] for row in q_b], clr=False)
    accs, done = await read_tile(dut)

    expected_sum = [a + b for a, b in zip(raw_acc(q_a, xs_a), raw_acc(q_b, xs_b))]
    assert accs == expected_sum, f"missing clr: expected accumulate into old sum {expected_sum}, got {accs}"
    assert done == 0, "missing clr: done fired at the end of the bad row set, behavior changed"
