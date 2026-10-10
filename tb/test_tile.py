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


@cocotb.test()
async def tile_real_layer(dut):
    """Rows 0..TILE_ROWS-1 of q_pc, run on every calibration vector in the export, bit-exact."""
    await start_clock(dut)
    data = np.load(NPZ_PATH)
    q_rows = data["q_pc"][:TILE_ROWS].astype(int).tolist()
    x_vectors = data["x_cal_int"].astype(int).tolist()
    assert len(q_rows[0]) == K, f"layer K is {len(q_rows[0])}, TILE_K is {K}"
    x_all = np.array(x_vectors)
    assert -127 <= x_all.min() and x_all.max() <= 127, "activation outside [-127, 127] (golden.py contract)"
    for v, xs in enumerate(x_vectors):
        expected = raw_acc(q_rows, xs)
        got = await run_tile(dut, xs, q_rows)
        assert got == expected, f"calibration vector {v}: expected {expected}, got {got}"
