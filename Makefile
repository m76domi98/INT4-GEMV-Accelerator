# One entry point per stage. Run from the repo root.
# Simulator: icarus (default) or verilator. Set on the command line: make test SIM=verilator

SIM ?= icarus
TOPLEVEL_LANG := verilog
TOPLEVEL := smoke_top
MODULE := test_smoke
VERILOG_SOURCES := $(wildcard rtl/*.sv)
export PYTHONPATH := $(CURDIR)/tb:$(CURDIR)/model:$(PYTHONPATH)

ifeq ($(SIM),icarus)
COMPILE_ARGS += -g2012
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: test test-pe test-tile test-requant test-layer test-layer-full test-layer-sticky export golden results

EXPORT_NPZ := export/out/layer15_up_proj.npz

test: sim

# Per-module targets. Each one overrides the toplevel, test module, and sources for that module.
test-pe:
	$(MAKE) sim TOPLEVEL=pe MODULE=test_pe VERILOG_SOURCES=rtl/pe.sv SIM_BUILD=sim_build/pe

# Tile size and K are parameters. Icarus only for now: it does not work under Verilator yet (Verilator needs -G, not -P). Override: make test-tile TILE_ROWS=2
TILE_ROWS ?= 4
TILE_K ?= 576
test-tile:
	TILE_ROWS=$(TILE_ROWS) TILE_K=$(TILE_K) COMPILE_ARGS="-Ppe_tile.TILE_ROWS=$(TILE_ROWS) -Ppe_tile.K=$(TILE_K)" $(MAKE) sim TOPLEVEL=pe_tile MODULE=test_tile VERILOG_SOURCES="rtl/pe.sv rtl/pe_tile.sv" SIM_BUILD=sim_build/pe_tile

LAYER_SOURCES := rtl/layer_ctrl.sv rtl/pe.sv rtl/pe_tile.sv rtl/requant.sv

test-requant:
	rm -rf sim_build/requant
	$(MAKE) sim TOPLEVEL=requant MODULE=test_requant VERILOG_SOURCES=rtl/requant.sv SIM_BUILD=sim_build/requant

# Routine: two vectors plus a repeat from reset. Slow, log the runtime in results.
test-layer:
	rm -rf sim_build/layer
	$(MAKE) sim TOPLEVEL=layer_ctrl MODULE=test_layer VERILOG_SOURCES="$(LAYER_SOURCES)" SIM_BUILD=sim_build/layer

# All 175 vectors, run once and logged. Hours under Icarus, not part of routine regression.
test-layer-full:
	FULL=1 $(MAKE) test-layer

# Broken copy: drops clr on term 0 of group 1. The sed must change the copy, or the test would pass on a good design.
test-layer-sticky:
	mkdir -p sim_build/broken
	sed 's/clr_pipe\[0\] <= issue_clr;/clr_pipe[0] <= issue_clr \&\& (grp != 1);/' rtl/layer_ctrl.sv > sim_build/broken/layer_ctrl.sv
	grep -q 'grp != 1' sim_build/broken/layer_ctrl.sv
	rm -rf sim_build/layer_sticky
	$(MAKE) sim TOPLEVEL=layer_ctrl MODULE=test_layer_sticky VERILOG_SOURCES="sim_build/broken/layer_ctrl.sv rtl/pe.sv rtl/pe_tile.sv rtl/requant.sv" SIM_BUILD=sim_build/layer_sticky

$(EXPORT_NPZ): export/export_layer.py
	python3 export/export_layer.py

export: $(EXPORT_NPZ)

golden: $(EXPORT_NPZ)
	python3 model/check_golden.py | tee results/stage1_golden.log

results:
	@echo "make results: not implemented yet (Stage 6, results/)" && exit 1
