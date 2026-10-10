"""Full-layer tests (Stage 3): rtl/layer_ctrl.sv on real exported data, bit-exact against gemv_int.

Every run starts from reset, loads weights, M_r, and activations through the LOAD ports, then runs the layer.
Routine (make test-layer): x_cal_int[0] and x_test_int[0], then a repeat of the first to check that two runs
from reset give identical outputs and cycle counts. FULL=1 (make test-layer-full) runs all 175 vectors.

Ports: clk, rst, start, load_done, w_we/w_addr/w_wdata, m_we/m_addr/m_wdata, x_we/x_addr/x_wdata,
out_raddr/out_rdata, layer_done, err_sticky, sat_count, compute_cycles, load_cycles.
Probes: t_valid, t_clr, t_x, t_w, the term the tile samples on the next edge. Checked on every term.
"""
import os

import cocotb
from golden import gemv_int

from layer_helpers import ROWS, load_layer, run_layer, start_clock

FULL = os.environ.get("FULL") == "1"
RESULTS = {}  # name -> run result, filled by the first test, read by the repeat test


def vector_set(layer):
    """(name, x_row) pairs for this run: the two routine vectors, or all 175 with FULL=1."""
    if not FULL:
        return [("cal0", layer["x_cal"][0]), ("test0", layer["x_test"][0])]
    return [(f"cal{i}", x) for i, x in enumerate(layer["x_cal"])] + [
        (f"test{i}", x) for i, x in enumerate(layer["x_test"])
    ]


@cocotb.test()
async def layer_matches_golden(dut):
    """Every row of every vector in the set equals gemv_int, the saturation count matches, no term or sticky error."""
    start_clock(dut)
    layer = load_layer()
    for name, x_row in vector_set(layer):
        expected_y, _, expected_sat = gemv_int(layer["q_rows"], x_row, layer["m"])
        result = await run_layer(dut, layer, x_row)
        dut._log.info(
            f"{name}: compute {result['compute_cycles']} load {result['load_cycles']} "
            f"sat {result['sat']} wall {result['wall_s']:.1f} s"
        )
        assert not result["errors"], f"{name}: term check failed: {result['errors']}"
        assert result["err_sticky"] == 0, f"{name}: err_sticky set on a good run"
        assert result["sat"] == expected_sat, f"{name}: sat_count {result['sat']}, golden {expected_sat}"
        bad_rows = [r for r in range(ROWS) if result["y"][r] != expected_y[r]]
        assert not bad_rows, (
            f"{name}: {len(bad_rows)} rows differ from gemv_int, first rows {bad_rows[:8]}: "
            f"got {[result['y'][r] for r in bad_rows[:8]]}, expected {[expected_y[r] for r in bad_rows[:8]]}"
        )
        RESULTS[name] = result


@cocotb.test()
async def repeat_from_reset_is_identical(dut):
    """The first vector, run again from reset, gives the same outputs, saturation count, and cycle counts."""
    start_clock(dut)
    layer = load_layer()
    name, x_row = vector_set(layer)[0]
    assert name in RESULTS, "layer_matches_golden did not record a first run"
    first = RESULTS[name]
    again = await run_layer(dut, layer, x_row)
    assert again["y"] == first["y"], f"{name}: outputs differ between two runs from reset"
    assert again["sat"] == first["sat"], f"{name}: saturation count differs between runs"
    assert again["compute_cycles"] == first["compute_cycles"], "compute cycles differ between runs"
    assert again["load_cycles"] == first["load_cycles"], "load cycles differ between runs"
