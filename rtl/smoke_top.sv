// Smoke-test module for the cocotb setup. Replaced by the real datapath in Stage 2.
module smoke_top (
    input  logic       clk,
    input  logic [3:0] d,   // data in, sampled on the clock edge
    output logic [3:0] q    // registered copy of d, one cycle late
);
    always_ff @(posedge clk) q <= d;  // plain flop, <= so q updates at the edge not mid-cycle
endmodule
