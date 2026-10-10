// Layer control for one up_proj run: loads memories, walks the row groups through the tile, requantizes each row.
// Design: docs/design/03-control-memory.md. Stage 3 tests READ_LAT = 1 only.
module layer_ctrl #(
    parameter int TILE_ROWS = 4,
    parameter int K        = 576,   // terms per row set
    parameter int ROWS     = 1536,  // output rows of the layer
    parameter int READ_LAT = 1      // memory read stages between the address and the tile
) (
    input  logic              clk,
    input  logic              rst,         // synchronous, clears the counters, sticky error, and sat_count
    input  logic              start,       // pulse in IDLE, begins a run
    input  logic              load_done,   // pulse in LOAD, ends the load
    input  logic              w_we,        // LOAD only: weight word write
    input  logic [17:0]       w_addr,      // word index g*K + t
    input  logic [15:0]       w_wdata,
    input  logic              m_we,        // LOAD only: M_r write
    input  logic [10:0]       m_addr,
    input  logic [15:0]       m_wdata,
    input  logic              x_we,        // LOAD only: activation write
    input  logic [9:0]        x_addr,
    input  logic [7:0]        x_wdata,
    input  logic [10:0]       out_raddr,
    output logic signed [7:0] out_rdata,   // combinational read of the output buffer
    output logic              layer_done,  // one cycle, output buffer valid
    output logic              err_sticky,  // set on any tile/control mismatch, cleared only by rst
    output logic [10:0]       sat_count,   // requant saturations in this run
    output logic [31:0]       compute_cycles,
    output logic [31:0]       load_cycles,
    output logic              t_valid,     // probes: the term the tile samples on the next edge
    output logic              t_clr,
    output logic [7:0]        t_x,
    output logic [15:0]       t_w
);
    localparam int GROUPS  = ROWS / TILE_ROWS;  // 384 row groups
    localparam int WORDS   = GROUPS * K;        // 221184 weight words
    localparam int WORD_W  = $clog2(WORDS);     // 18
    localparam int GRP_W   = $clog2(GROUPS);    // 9
    localparam int TERM_W  = $clog2(K);         // 10
    localparam int ROW_W   = $clog2(ROWS);      // 11
    localparam int ACC_W   = 21;

    typedef enum logic [2:0] {IDLE, LOAD, COMPUTE, REQUANT, DONE} state_t;

    state_t             state;
    logic [GRP_W-1:0]   grp;       // row group being issued or requantized
    logic [TERM_W-1:0]  term;      // term being issued
    logic               issuing;   // COMPUTE is still sending terms for this group
    logic [1:0]         rq_r;      // which tile row REQUANT is on

    // memories, written in LOAD, read in COMPUTE and REQUANT
    logic [15:0]        w_mem [WORDS];
    logic signed [15:0] m_mem [ROWS];
    logic [7:0]         x_mem [K];
    logic signed [7:0]  out_mem [ROWS];

    // ---- load writes ----
    always_ff @(posedge clk) begin
        if (state == LOAD) begin
            if (w_we) w_mem[w_addr] <= w_wdata;
            if (m_we) m_mem[m_addr] <= m_wdata;
            if (x_we) x_mem[x_addr] <= x_wdata;
        end
    end

    // ---- issue side: address and term selection ----
    logic [WORD_W-1:0] addr_now;
    logic              issue_clr;
    assign addr_now  = WORD_W'(grp) * WORD_W'(K) + WORD_W'(term);
    assign issue_clr = (term == '0);  // term 0 of each row set restarts the tile

    // read pipe: the address goes in at the first stage, the tile takes the last stage READ_LAT - 1 cycles later
    logic [15:0] w_pipe     [READ_LAT];
    logic [7:0]  x_pipe     [READ_LAT];
    logic        v_pipe     [READ_LAT];
    logic        clr_pipe   [READ_LAT];
    logic        first_pipe [READ_LAT];  // intended term 0, carried alongside clr for the sticky check

    always_ff @(posedge clk) begin
        w_pipe[0]     <= w_mem[addr_now];
        x_pipe[0]     <= x_mem[term];
        v_pipe[0]     <= issuing;
        clr_pipe[0] <= issue_clr;  // the sticky mutant in make test-layer-sticky matches this exact line
        first_pipe[0] <= (term == '0);
        for (int i = 1; i < READ_LAT; i++) begin
            w_pipe[i]     <= w_pipe[i-1];
            x_pipe[i]     <= x_pipe[i-1];
            v_pipe[i]     <= v_pipe[i-1];
            clr_pipe[i]   <= clr_pipe[i-1];
            first_pipe[i] <= first_pipe[i-1];
        end
    end

    assign t_valid = v_pipe[READ_LAT-1];
    assign t_clr   = clr_pipe[READ_LAT-1];
    assign t_x     = x_pipe[READ_LAT-1];
    assign t_w     = w_pipe[READ_LAT-1];

    // ---- tile ----
    logic [ACC_W*TILE_ROWS-1:0] tile_acc;
    logic                       tile_done;
    logic signed [7:0]          tile_x;
    assign tile_x = t_x;

    pe_tile #(.TILE_ROWS(TILE_ROWS), .K(K)) u_tile (
        .clk     (clk),
        .in_valid(t_valid),
        .clr     (t_clr),
        .x       (tile_x),
        .w       (t_w),
        .acc     (tile_acc),
        .done    (tile_done)
    );

    // ---- sticky check: the control's own count of accepted terms, compared with the tile's done ----
    logic [TERM_W-1:0] ecnt;         // accepted terms so far in this row set
    logic              expect_done;  // same edge as the tile's done, one cycle after the Kth accepted term
    logic [TERM_W-1:0] ecur;         // index of the term arriving now
    assign ecur = first_pipe[READ_LAT-1] ? '0 : ecnt;  // intended term 0 restarts the count

    always_ff @(posedge clk) begin
        if (rst) begin
            ecnt        <= '0;
            expect_done <= 1'b0;
        end else if (t_valid) begin
            ecnt        <= ecur + 1'b1;
            expect_done <= (ecur == TERM_W'(K - 1));
        end else begin
            expect_done <= 1'b0;
        end
    end

    wire checking = (state == COMPUTE) || (state == REQUANT);

    always_ff @(posedge clk) begin
        if (rst)
            err_sticky <= 1'b0;
        else if (checking && (tile_done != expect_done))
            err_sticky <= 1'b1;  // sticky: holds until rst
    end

    // ---- requant: fed only in REQUANT, so the sat counter sees no garbage ----
    logic [ROW_W-1:0]          row_idx;   // grp * TILE_ROWS + rq_r, TILE_ROWS = 4 so this is just {grp, rq_r}
    logic                      rq_active;
    logic signed [ACC_W-1:0]   rq_acc;
    logic signed [15:0]        rq_m;
    logic signed [7:0]         rq_y;
    logic                      rq_sat;
    logic                      start_clear;

    assign row_idx     = {grp, rq_r};
    assign rq_active   = (state == REQUANT);
    assign rq_acc      = rq_active ? tile_acc[ACC_W*rq_r +: ACC_W] : '0;  // zero acc gives y = 0, no sat
    assign rq_m        = rq_active ? m_mem[row_idx] : '0;
    assign start_clear = (state == IDLE) && start;

    requant u_requant (
        .clk      (clk),
        .rst      (rst),
        .clr_count(start_clear),
        .acc      (rq_acc),
        .m        (rq_m),
        .y        (rq_y),
        .sat      (rq_sat),
        .sat_count(sat_count)
    );

    always_ff @(posedge clk) begin
        if (rq_active)
            out_mem[row_idx] <= rq_y;
    end

    assign out_rdata = out_mem[out_raddr];

    // ---- FSM ----
    assign layer_done = (state == DONE);

    always_ff @(posedge clk) begin
        if (rst) begin
            state          <= IDLE;
            grp            <= '0;
            term           <= '0;
            issuing        <= 1'b0;
            rq_r           <= '0;
            compute_cycles <= '0;
            load_cycles    <= '0;
        end else begin
            case (state)
                IDLE: if (start) begin
                    state          <= LOAD;
                    compute_cycles <= '0;
                    load_cycles    <= '0;
                end

                LOAD: begin
                    load_cycles <= load_cycles + 1'b1;
                    if (load_done) begin
                        state   <= COMPUTE;
                        grp     <= '0;
                        term    <= '0;
                        issuing <= 1'b1;
                    end
                end

                COMPUTE: begin
                    compute_cycles <= compute_cycles + 1'b1;
                    if (issuing) begin
                        if (term == TERM_W'(K - 1)) begin
                            term    <= '0;
                            issuing <= 1'b0;  // last term of this group is out, now wait for expect_done
                        end else begin
                            term <= term + 1'b1;
                        end
                    end else if (expect_done) begin
                        state <= REQUANT;
                        rq_r  <= '0;
                    end
                end

                REQUANT: begin
                    compute_cycles <= compute_cycles + 1'b1;
                    rq_r           <= rq_r + 1'b1;
                    if (rq_r == 2'(TILE_ROWS - 1)) begin
                        if (grp == GRP_W'(GROUPS - 1)) begin
                            state <= DONE;
                        end else begin
                            grp     <= grp + 1'b1;
                            issuing <= 1'b1;
                            state   <= COMPUTE;
                        end
                    end
                end

                DONE: state <= IDLE;

                default: state <= IDLE;
            endcase
        end
    end
endmodule
