// Output-stationary tile: TILE_ROWS PEs share one broadcast x, each with its own weight. Raw accumulators out, no requant.
module pe_tile #(
    parameter int TILE_ROWS = 4,    // output rows per tile
    parameter int K         = 576,  // terms per dot product (up_proj K in Stage 1)
    parameter int PROD_W    = 11,   // passed to each PE
    parameter int ACC_W     = 21    // passed to each PE
) (
    input  logic                            clk,
    input  logic                            in_valid,  // this cycle carries a real term
    input  logic                            clr,       // with in_valid: this is term 0 of a new row set
    input  logic signed [7:0]               x,         // INT8 activation, same for every row
    input  logic        [4*TILE_ROWS-1:0]   w,         // INT4 weights, row r at bits [4r+3:4r]
    output logic        [ACC_W*TILE_ROWS-1:0] acc,     // row r at bits [ACC_W*r+ACC_W-1 : ACC_W*r]
    output logic                            done       // one cycle after the Kth valid term, acc is final then
);
    // term counter, one more bit than needed for K so K itself fits
    localparam int CNT_W = $clog2(K + 1);

    logic [CNT_W-1:0] term_idx;  // index of the next term in the current row set
    logic [CNT_W-1:0] cur_idx;   // index of the term arriving now
    logic signed [TILE_ROWS-1:0][ACC_W-1:0] row_acc;  // one accumulator per PE, packed for the port slices

    // clr restarts the count, so the term it arrives with is index 0
    assign cur_idx = clr ? '0 : term_idx;

    always_ff @(posedge clk) begin
        done <= 1'b0;  // default: done is a one-cycle pulse
        if (in_valid) begin
            term_idx <= cur_idx + 1'b1;
            done     <= (cur_idx == CNT_W'(K - 1));  // the Kth term lands at index K-1
        end
    end

    genvar r;
    generate
        for (r = 0; r < TILE_ROWS; r++) begin : g_row
            pe #(.PROD_W(PROD_W), .ACC_W(ACC_W)) u_pe (
                .clk     (clk),
                .in_valid(in_valid),
                .clr     (clr),
                .x       (x),
                .w       (w[4*r +: 4]),  // this row's own weight
                .acc     (row_acc[r])
            );
            assign acc[ACC_W*r +: ACC_W] = row_acc[r];  // pack into the flat output bus
        end
    endgenerate
endmodule
