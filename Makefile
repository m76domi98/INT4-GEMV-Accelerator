# One entry point per stage. Run from the repo root.
# Simulator: icarus (default) or verilator. Set on the command line: make test SIM=verilator

SIM ?= icarus
TOPLEVEL_LANG := verilog
TOPLEVEL := smoke_top
MODULE := test_smoke
VERILOG_SOURCES := $(wildcard rtl/*.sv)
export PYTHONPATH := $(CURDIR)/tb:$(PYTHONPATH)

ifeq ($(SIM),icarus)
COMPILE_ARGS += -g2012
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: test test-pe export golden results

EXPORT_NPZ := export/out/layer15_up_proj.npz

test: sim

# Per-module targets. Each one overrides the toplevel, test module, and sources for that module.
test-pe:
	$(MAKE) sim TOPLEVEL=pe MODULE=test_pe VERILOG_SOURCES=rtl/pe.sv SIM_BUILD=sim_build/pe

$(EXPORT_NPZ): export/export_layer.py
	python3 export/export_layer.py

export: $(EXPORT_NPZ)

golden: $(EXPORT_NPZ)
	python3 model/check_golden.py | tee results/stage1_golden.log

results:
	@echo "make results: not implemented yet (Stage 6, results/)" && exit 1
