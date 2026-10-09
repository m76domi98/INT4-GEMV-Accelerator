import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


@cocotb.test()
async def registers_input_on_clock_edge(dut):
    """The smoke module must register d on the rising clock edge."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())  # clock runs in the background or RisingEdge never fires

    dut.d.value = 5  # set the input before the edge so the flop has something to grab
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")  # wait a hair past the edge so q has settled before we read it

    assert dut.q.value == 5, f"expected q=5, got {dut.q.value}"
