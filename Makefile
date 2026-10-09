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

.PHONY: test export results

test: sim

export:
	@echo "make export: not implemented yet (Stage 1, export/)" && exit 1

results:
	@echo "make results: not implemented yet (Stage 6, results/)" && exit 1
