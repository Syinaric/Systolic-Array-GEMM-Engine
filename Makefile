SIM ?= icarus
TOPLEVEL_LANG ?= verilog

MODULE_NAME ?= delay

DEPTH      ?= 4
DATA_WIDTH ?= 8
ACC_WIDTH  ?= 32
K          ?= 8
SEED ?=
export SEED
export K

VERILOG_SOURCES += $(PWD)/rtl/$(MODULE_NAME).sv

COCOTB_TOPLEVEL     = $(MODULE_NAME)
COCOTB_TEST_MODULES = test_$(MODULE_NAME)

export PYTHONPATH := $(PWD)/tb:$(PWD)/model:$(PYTHONPATH)

COMPILE_ARGS += -g2012

ifeq ($(MODULE_NAME),delay)
COMPILE_ARGS += -Pdelay.DEPTH=$(DEPTH)
COMPILE_ARGS += -Pdelay.DATA_WIDTH=$(DATA_WIDTH)
SIM_BUILD = sim_build/delay_depth_$(DEPTH)
endif

ifeq ($(MODULE_NAME),pe)
COMPILE_ARGS += -Ppe.DATA_WIDTH=$(DATA_WIDTH)
COMPILE_ARGS += -Ppe.ACC_WIDTH=$(ACC_WIDTH)
SIM_BUILD = sim_build/pe_k_$(K)_acc_$(ACC_WIDTH)
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: sweep sweep-pe sweep-all

sweep:
	@for d in 0 1 2 4 8; do \
	  echo "=== DEPTH=$$d ==="; \
	  $(MAKE) -s MODULE_NAME=delay DEPTH=$$d || exit 1; \
	done
	@echo "=== delay sweep passed ==="

sweep-pe:
	@for k in 1 2 8 64 255; do \
	  echo "=== K=$$k ==="; \
	  $(MAKE) -s MODULE_NAME=pe K=$$k || exit 1; \
	done
	@echo "=== K=16 ACC_WIDTH=18 (deliberate overflow) ==="
	@$(MAKE) -s MODULE_NAME=pe K=16 ACC_WIDTH=18 || exit 1
	@echo "=== pe sweep passed ==="

sweep-all: sweep sweep-pe