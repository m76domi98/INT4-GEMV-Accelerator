"""Sticky-error test (Stage 3). Runs against the broken copy sim_build/broken/layer_ctrl.sv, built by make test-layer-sticky.

The copy drops clr on term 0 of group 1, so the tile never restarts that row set. Production RTL has no fault hook.
Checks: err_sticky is set by the run, stays set through idle cycles after done, and clears only on reset.
The term monitor also fails on this copy, which is expected here, so its errors are not asserted in this file.
"""
import cocotb
from cocotb.triggers import FallingEdge

from layer_helpers import load_layer, reset, run_layer, start_clock

IDLE_CYCLES_AFTER_DONE = 100


@cocotb.test()
async def sticky_set_holds_and_clears_only_on_reset(dut):
    """A faulty run must set err_sticky. It must stay set through idle cycles, and only reset clears it."""
    start_clock(dut)
    layer = load_layer()
    result = await run_layer(dut, layer, layer["x_cal"][0])
    assert result["err_sticky"] == 1, "faulty copy did not set err_sticky, the check cannot catch a missing clr"

    for _ in range(IDLE_CYCLES_AFTER_DONE):
        await FallingEdge(dut.clk)
    assert int(dut.err_sticky.value) == 1, "err_sticky cleared during idle cycles, it must hold until reset"

    await reset(dut)
    assert int(dut.err_sticky.value) == 0, "reset did not clear err_sticky"
