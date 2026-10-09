// Smoke-test module for the cocotb setup. Replaced by the real datapath in Stage 2.
module smoke_top (
    input  logic       clk,
    input  logic [3:0] d,
    output logic [3:0] q
);
    always_ff @(posedge clk) q <= d;
endmodule
