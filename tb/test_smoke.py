import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


@cocotb.test()
async def registers_input_on_clock_edge(dut):
    """The smoke module must register d on the rising clock edge."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    dut.d.value = 5
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert dut.q.value == 5, f"expected q=5, got {dut.q.value}"
