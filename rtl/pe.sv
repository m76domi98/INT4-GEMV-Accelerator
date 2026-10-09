// One MAC PE for the output-stationary tile. It holds one accumulator and knows nothing about K or its row position.
module pe #(
    parameter int PROD_W = 11,  // signed product width, product range [-1016, 1016]
    parameter int ACC_W  = 21   // signed accumulator width, worst case 576 * 1016 = 585,216
) (
    input  logic                    clk,
    input  logic                    in_valid,  // this cycle carries a real term, idle cycles leave acc alone
    input  logic                    clr,       // with in_valid: load acc with this term instead of adding to it
    input  logic signed [7:0]       x,         // INT8 activation, broadcast to every PE in the tile
    input  logic signed [3:0]       w,         // INT4 weight, this row's own
    output logic signed [ACC_W-1:0] acc        // holds until the next clr
);
    // widen x and w to the product width before multiplying, so the product does not wrap
    logic signed [PROD_W-1:0] x_ext;
    logic signed [PROD_W-1:0] w_ext;
    logic signed [PROD_W-1:0] prod;
    logic signed [ACC_W-1:0]  prod_ext;

    assign x_ext    = x;
    assign w_ext    = w;
    assign prod     = x_ext * w_ext;
    assign prod_ext = prod;  // sign-extend the product to the accumulator width

    always_ff @(posedge clk) begin
        if (in_valid)
            acc <= clr ? prod_ext : acc + prod_ext;  // clr restarts the row, otherwise accumulate
    end
endmodule
