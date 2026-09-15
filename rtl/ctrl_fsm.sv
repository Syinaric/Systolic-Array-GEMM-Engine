//ctrl_fsm is the tile sequencer for the NxN output stationary array. 

// this block owns the timing, not the data. it omits a slice index 'k_idx' and the 
//feeder supplies the operand bytes MEM_LATENCY cycles later. 
//the tile tags travel thru delay lines of the same depth so that they arrive at the array boundry on the same 
//edge as the operands they tag. 

module ctrl_fsm #( 
    parameter int N = 8, 
    parameter int K_WIDTH = 16, 
    parameter int MEM_LATENCY = 1,
    parameter int ROW_W = (N > 1) ? $clog2(N) : 1
)( 
    input logic clk, 
    input logic reset,    //synchronous


    input  logic start,
    input  logic [K_WIDTH-1:0] k_in,
    output logic ready,
    output logic busy,
    output logic done,
 
    // operand feeder side
    input  logic stall,
    output logic op_req,
    output logic [K_WIDTH-1:0] k_idx,
 
    // systolic array side
    output logic arr_en,
    output logic arr_first,
    output logic arr_last,
    output logic arr_drain_shift,
 
    // result side
    output logic c_valid,
    output logic [ROW_W-1:0] c_row
    ); 