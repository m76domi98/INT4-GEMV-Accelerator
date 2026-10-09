"""PE tests (Stage 2): bit-exact against a Python int reference.

Each term adds x * w to acc. clr=1 on term 0 loads acc with that first product,
so the next row starts clean. acc holds until the next clr. Port names:
clk, in_valid, clr, x (INT8, two's complement), w (INT4, two's complement), acc.
"""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

X_VALUES = [-127, -1, 0, 1, 127]  # INT8 range in golden.py is [-127, 127]; -128 is out of range, not tested
W_VALUES = list(range(-8, 8))  # INT4, [-8, 7]
X_NAMES = {-127: "int8_min", -1: "int8_neg1", 0: "int8_zero", 1: "int8_one", 127: "int8_max"}
W_NAMES = {-8: "int4_min", 7: "int4_max"}
WORST_K = 576  # K of up_proj in Stage 1; worst |acc| is WORST_K * 1016 = 585,216
WORST_PRODUCT_ABS = 1016  # 127 * 8, the largest |x * w|
RANDOM_SEED = 2  # fixed so a failure reproduces
RANDOM_RUNS = 200
CLOCK_PERIOD_NS = 10


def case_name(x, w):
    """Test name for one (x, w) corner, e.g. int8_min_x_int4_max."""
    w_name = W_NAMES.get(w) or (f"int4_neg{-w}" if w < 0 else f"int4_{w}")
    return f"{X_NAMES[x]}_x_{w_name}"


async def start_clock(dut):
    """Start the clock and drive all inputs to zero before the first term."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, units="ns").start())
    dut.in_valid.value = 0
    dut.clr.value = 0
    dut.x.value = 0
    dut.w.value = 0


async def send_term(dut, x, w, clr):
    """Drive one valid term on the falling edge, so it is sampled on the next rising edge."""
    await FallingEdge(dut.clk)
    dut.in_valid.value = 1
    dut.clr.value = int(clr)
    dut.x.value = x & 0xFF  # mask to the 8-bit bus, two's complement
    dut.w.value = w & 0xF  # mask to the 4-bit bus, two's complement
    await RisingEdge(dut.clk)


async def idle_cycles(dut, cycles, x_junk, w_junk):
    """Hold in_valid low for some cycles, driving junk on x and w to prove they are ignored."""
    for _ in range(cycles):
        await FallingEdge(dut.clk)
        dut.in_valid.value = 0
        dut.clr.value = 0
        dut.x.value = x_junk & 0xFF
        dut.w.value = w_junk & 0xF
        await RisingEdge(dut.clk)


async def read_acc(dut):
    """Read acc a hair after the edge, so the flop has settled (same as the smoke test)."""
    await Timer(1, units="ns")
    return dut.acc.value.signed_integer


async def run_dot(dut, xs, ws):
    """Accumulate one dot product. clr is asserted on term 0 only."""
    for i, (x, w) in enumerate(zip(xs, ws)):
        await send_term(dut, x, w, clr=(i == 0))
    return await read_acc(dut)


async def corner_body(dut, x, w):
    """One product with clr, then the same product again without clr, so accumulate is checked too."""
    await start_clock(dut)

    await send_term(dut, x, w, clr=True)
    got = await read_acc(dut)
    assert got == x * w, f"clr term: x={x} w={w} expected {x * w}, got {got}"

    await send_term(dut, x, w, clr=False)
    got = await read_acc(dut)
    assert got == 2 * x * w, f"second term: x={x} w={w} expected {2 * x * w}, got {got}"


def make_corner_test(x, w):
    """Build one named cocotb test per corner. cocotb needs a separate Test object for each name."""

    @cocotb.test(name=case_name(x, w))
    async def corner_test(dut):
        await corner_body(dut, x, w)

    return corner_test


for _x in X_VALUES:
    for _w in W_VALUES:
        globals()[f"test_{case_name(_x, _w)}"] = make_corner_test(_x, _w)


async def worst_case_body(dut, x, w, expected):
    """WORST_K terms of the same product, the largest |acc| the layer can reach."""
    await start_clock(dut)
    got = await run_dot(dut, [x] * WORST_K, [w] * WORST_K)
    assert got == expected, f"worst case x={x} w={w} K={WORST_K}: expected {expected}, got {got}"


@cocotb.test()
async def worst_case_positive_acc(dut):
    """x=-127, w=-8 gives the largest positive product, +1016, over K terms."""
    await worst_case_body(dut, -127, -8, WORST_K * WORST_PRODUCT_ABS)


@cocotb.test()
async def worst_case_negative_acc(dut):
    """x=127, w=-8 gives the largest negative product, -1016, over K terms."""
    await worst_case_body(dut, 127, -8, -WORST_K * WORST_PRODUCT_ABS)


@cocotb.test()
async def random_dot_products(dut):
    """Random (x, w) dot products of random length, each started with clr, all bit-exact."""
    await start_clock(dut)
    rng = random.Random(RANDOM_SEED)
    for run in range(RANDOM_RUNS):
        k = rng.randint(1, WORST_K)
        xs = [rng.randint(-127, 127) for _ in range(k)]
        ws = [rng.randint(-8, 7) for _ in range(k)]
        expected = sum(x * w for x, w in zip(xs, ws))
        got = await run_dot(dut, xs, ws)
        assert got == expected, f"random run {run} K={k}: expected {expected}, got {got}"


@cocotb.test()
async def acc_holds_while_idle(dut):
    """With in_valid low, acc does not change even while x and w are driven with junk."""
    await start_clock(dut)
    before = await run_dot(dut, [5, -7, 100], [3, -8, 7])
    await idle_cycles(dut, cycles=5, x_junk=-127, w_junk=-8)
    after = await read_acc(dut)
    assert after == before, f"acc changed while idle: before={before}, after={after}"
