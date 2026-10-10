// Requant for one output row: y = clamp((acc * m + 2^14) >>> 15, -128, 127), same as gemv_int.
// y and sat are combinational. sat_count is registered, counts clipped outputs, and clr_count clears it at run start.
// rst clears sat_count too, so it has a known value before the first run.
module requant #(
    parameter int ACC_W  = 21,  // signed accumulator width, range [-2^20, 2^20 - 1]
    parameter int M_W    = 16,  // signed requant multiplier width
    parameter int PROD_W = 40,  // 21 + 16 = 37 bits is enough, 40 leaves room so the rounding cannot overflow
    parameter int CNT_W  = 11   // one run has at most 1,536 rows, so 11 bits holds it without wrapping
) (
    input  logic                    clk,
    input  logic                    rst,        // synchronous reset, clears sat_count
    input  logic                    clr_count,  // clears sat_count, the control asserts it at the start of each run
    input  logic signed [ACC_W-1:0] acc,
    input  logic signed [M_W-1:0]   m,
    output logic signed [7:0]       y,          // INT8, clamped
    output logic                    sat,        // this output was clipped
    output logic [CNT_W-1:0]        sat_count   // clipped outputs in the current run
);
    localparam logic signed [PROD_W-1:0] ROUND = 40'sd16384;  // 2^14, round half up before the shift
    localparam int SHIFT = 15;

    logic signed [PROD_W-1:0] prod;
    logic signed [PROD_W-1:0] shifted;

    assign prod    = PROD_W'(acc) * PROD_W'(m);  // widen both before multiplying so the product does not wrap
    assign shifted = (prod + ROUND) >>> SHIFT;   // arithmetic shift, rounds toward -inf like gemv_int

    always_comb begin
        if (shifted < -128) begin
            y   = -8'sd128;
            sat = 1'b1;
        end else if (shifted > 127) begin
            y   = 8'sd127;
            sat = 1'b1;
        end else begin
            y   = shifted[7:0];
            sat = 1'b0;
        end
    end

    always_ff @(posedge clk) begin
        if (rst || clr_count)
            sat_count <= '0;
        else if (sat)
            sat_count <= sat_count + 1'b1;
    end
endmodule
