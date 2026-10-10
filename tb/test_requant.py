"""Requant tests (Stage 3): rtl/requant.sv against gemv_int's formula, bit-exact.

Port names: clk, clr_count, acc (21-bit signed), m (16-bit signed), y (INT8), sat, sat_count (11 bits).
y and sat are combinational from acc and m. sat_count counts clipped outputs and is cleared by clr_count.
"""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from golden import REQUANT_ROUND, REQUANT_SHIFT, Y_MAX, Y_MIN, gemv_int, raw_acc

ACC_MIN = -(1 << 20)  # 21-bit signed range is [-2^20, 2^20 - 1]; +2^20 does not fit
ACC_MAX = (1 << 20) - 1
M_EXPORT_VALUES = [1723, 30917]  # min and max M_r in the exported m_pc
M_MIN_16 = -(1 << 15)
M_MAX_16 = (1 << 15) - 1
RANDOM_SEED = 3  # fixed so a failure reproduces
RANDOM_RUNS = 500
CLOCK_PERIOD_NS = 10


def expected_requant(acc, m):
    """The same line as gemv_int, applied to one accumulator. Returns (y, saturated)."""
    y = (acc * m + REQUANT_ROUND) >> REQUANT_SHIFT
    return min(max(y, Y_MIN), Y_MAX), not Y_MIN <= y <= Y_MAX


async def start(dut):
    """Start the clock, clear the counter, and drive a neutral input."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, units="ns").start())
    dut.clr_count.value = 0
    dut.acc.value = 0
    dut.m.value = 0
    await RisingEdge(dut.clk)


async def check_one(dut, acc, m):
    """Drive one (acc, m) pair, read y and sat after they settle, and compare with the formula."""
    dut.acc.value = acc & ((1 << 21) - 1)  # mask to the 21-bit bus, two's complement
    dut.m.value = m & 0xFFFF
    await Timer(1, units="ns")
    want_y, want_sat = expected_requant(acc, m)
    got_y = dut.y.value.signed_integer
    got_sat = int(dut.sat.value)
    assert got_y == want_y, f"acc={acc} m={m}: expected y={want_y}, got {got_y}"
    assert got_sat == int(want_sat), f"acc={acc} m={m}: expected sat={int(want_sat)}, got {got_sat}"


@cocotb.test()
async def formula_matches_gemv_int(dut):
    """Sanity check on the reference itself: expected_requant agrees with gemv_int on a real dot product."""
    rng = random.Random(RANDOM_SEED)
    q_rows = [[rng.randint(-8, 7) for _ in range(64)] for _ in range(8)]
    x_int = [rng.randint(-127, 127) for _ in range(64)]
    m_rows = [rng.randint(M_EXPORT_VALUES[0], M_EXPORT_VALUES[1]) for _ in range(8)]
    y_ref, _, _ = gemv_int(q_rows, x_int, m_rows)
    accs = raw_acc(q_rows, x_int)
    assert [expected_requant(a, m)[0] for a, m in zip(accs, m_rows)] == y_ref


@cocotb.test()
async def acc_extremes(dut):
    """The 21-bit accumulator extremes against every export M_r extreme."""
    await start(dut)
    for acc in (ACC_MIN, ACC_MAX, 0, 1, -1):
        for m in M_EXPORT_VALUES:
            await check_one(dut, acc, m)


@cocotb.test()
async def m_extremes_16bit(dut):
    """The full 16-bit signed range of M, at the accumulator extremes."""
    await start(dut)
    for m in (M_MIN_16, M_MAX_16, 0):
        for acc in (ACC_MIN, ACC_MAX):
            await check_one(dut, acc, m)


@cocotb.test()
async def random_accumulators(dut):
    """Random accumulators and M values across the whole ranges, fixed seed."""
    await start(dut)
    rng = random.Random(RANDOM_SEED)
    for _ in range(RANDOM_RUNS):
        await check_one(dut, rng.randint(ACC_MIN, ACC_MAX), rng.randint(M_MIN_16, M_MAX_16))


@cocotb.test()
async def sat_count_counts_and_clears(dut):
    """sat_count goes up once per clipped output, holds otherwise, and clr_count clears it."""
    await start(dut)
    big = (ACC_MAX, M_EXPORT_VALUES[1])  # saturates high
    small = (0, M_EXPORT_VALUES[0])  # does not saturate
    expected = 0
    for acc, m, clip in [(*big, True), (*small, False), (*big, True), (*small, False)]:
        dut.acc.value = acc & ((1 << 21) - 1)
        dut.m.value = m & 0xFFFF
        await FallingEdge(dut.clk)  # count is registered, so it moves on the next rising edge
        await RisingEdge(dut.clk)
        expected += int(clip)
    await Timer(1, units="ns")
    got = dut.sat_count.value.integer
    assert got == expected, f"sat_count: expected {expected}, got {got}"

    dut.clr_count.value = 1
    await FallingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")
    assert dut.sat_count.value.integer == 0, "clr_count did not clear sat_count"
