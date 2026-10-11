"""Shared helpers for the layer tests (Stage 3): data loading, memory writes, one layer run, and a term monitor.

Not a test module. test_layer.py and test_layer_sticky.py import it, and the cocotb tests live in those files.
Port names are listed in tb/test_layer.py and in docs/design/03-control-memory.md.
"""
import time
from pathlib import Path

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

TILE_ROWS = 4
K = 576  # terms per row set, up_proj K in Stage 1
ROWS = 1536  # output rows of the layer
GROUPS = ROWS // TILE_ROWS  # 384 row groups, each one tile run
WORDS = GROUPS * K  # one weight word per (group, term)
NPZ_PATH = Path(__file__).resolve().parents[1] / "export" / "out" / "layer15_up_proj.npz"
CLOCK_PERIOD_NS = 10
MAX_RUN_CYCLES = 5_000_000  # a run is about 223k compute cycles, this is a hang guard, not a budget
MAX_REPORTED_ERRORS = 5  # stop collecting term mismatches after this many, the first ones are enough
INPUT_NAMES = ("start", "load_done", "rst", "w_we", "m_we", "x_we")
# write port names per memory: (we, addr, data)
MEM_PORTS = {"w": ("w_we", "w_addr", "w_wdata"), "m": ("m_we", "m_addr", "m_wdata"), "x": ("x_we", "x_addr", "x_wdata")}


def load_layer():
    """Weights as packed words (row r of group g in bits [4r+3:4r], word index g*K + t), M_r, and both activation splits."""
    data = np.load(NPZ_PATH)
    q = data["q_pc"].astype(np.int64)
    nibbles = (q & 0xF).reshape(GROUPS, TILE_ROWS, K)
    words = np.zeros((GROUPS, K), dtype=np.int64)
    for r in range(TILE_ROWS):
        words |= nibbles[:, r, :] << (4 * r)  # same packing as pe_tile's w bus
    return {
        "q_rows": q.tolist(),
        "words": words.reshape(-1).tolist(),
        "m": data["m_pc"].astype(int).tolist(),
        "x_cal": data["x_cal_int"].astype(int).tolist(),
        "x_test": data["x_test_int"].astype(int).tolist(),
    }


def load_writes(layer, x_row):
    """Every write of one run, in order: all weight words, then M_r, then the activations."""
    writes = [("w", addr, word) for addr, word in enumerate(layer["words"])]
    writes += [("m", row, m & 0xFFFF) for row, m in enumerate(layer["m"])]  # M_r as 16-bit two's complement
    writes += [("x", t, x & 0xFF) for t, x in enumerate(x_row)]  # INT8 as 8-bit two's complement
    return writes


def start_clock(dut):
    """Start the clock and drive every input to zero."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, units="ns").start())
    for name in INPUT_NAMES:
        getattr(dut, name).value = 0
    dut.out_raddr.value = 0


async def reset(dut):
    """Hold rst for two cycles, then release it on a falling edge."""
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0


async def drive_load(dut, writes):
    """One write per cycle, set on the falling edge so the rising edge samples it. Then load_done for one cycle."""
    for kind, addr, value in writes:
        await FallingEdge(dut.clk)
        for name, (we, _, _) in MEM_PORTS.items():
            getattr(dut, we).value = int(name == kind)  # only the active memory's write enable is high
        we, addr_port, data_port = MEM_PORTS[kind]
        getattr(dut, addr_port).value = addr
        getattr(dut, data_port).value = value
    await FallingEdge(dut.clk)
    for we, _, _ in MEM_PORTS.values():
        getattr(dut, we).value = 0
    dut.load_done.value = 1
    await RisingEdge(dut.clk)
    dut.load_done.value = 0


async def watch_terms(dut, x_row, words, errors, progress):
    """Check every term the control presents to the tile against the expected stream.

    Sampled on the falling edge, so the values are the ones the tile takes on the next rising edge.
    Expected: clr on term 0 of each group only, the activation x[t], and the packed weight word for (group, t).
    progress["terms"] counts the accepted terms seen, so run_layer can tell a short run from a long one.
    """
    group = term = 0
    while group < GROUPS and not progress.get("stop"):
        await FallingEdge(dut.clk)
        if not int(dut.t_valid.value):
            continue
        expected = {"t_clr": int(term == 0), "t_x": x_row[term] & 0xFF, "t_w": words[group * K + term]}
        for name, want in expected.items():
            got = int(getattr(dut, name).value)
            if got != want and len(errors) < MAX_REPORTED_ERRORS:
                errors.append(f"group {group} term {term} {name}: expected {want}, got {got}")
        progress["terms"] += 1
        term += 1
        if term == K:
            term = 0
            group += 1


async def read_out(dut):
    """Read the output buffer, one row per address, a hair after the address settles."""
    y = []
    for row in range(ROWS):
        dut.out_raddr.value = row
        await Timer(1, units="ns")
        y.append(dut.out_rdata.value.signed_integer)
    return y


async def run_layer(dut, layer, x_row):
    """Reset, load, run one layer, and read back everything the tests compare. Returns a dict."""
    await reset(dut)
    errors = []
    progress = {"terms": 0}
    started = time.perf_counter()

    await FallingEdge(dut.clk)
    dut.start.value = 1
    await FallingEdge(dut.clk)
    dut.start.value = 0
    monitor = cocotb.start_soon(watch_terms(dut, x_row, layer["words"], errors, progress))

    await drive_load(dut, load_writes(layer, x_row))

    for _ in range(MAX_RUN_CYCLES):
        await FallingEdge(dut.clk)
        if int(dut.layer_done.value):
            break
    else:
        raise AssertionError(f"layer did not finish within {MAX_RUN_CYCLES} cycles")

    result = {
        "compute_cycles": dut.compute_cycles.value.integer,
        "load_cycles": dut.load_cycles.value.integer,
        "sat": dut.sat_count.value.integer,
        "err_sticky": int(dut.err_sticky.value),
        "y": await read_out(dut),
    }
    # A DUT that finishes early never completes the term stream. Stop the monitor at its next edge and report the shortfall.
    progress["stop"] = True
    await monitor
    if progress["terms"] != WORDS:
        errors.append(f"control presented {progress['terms']} terms, expected {WORDS}")
    result["errors"] = errors
    result["wall_s"] = time.perf_counter() - started
    return result
