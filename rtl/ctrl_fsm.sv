//ctrl_fsm is the tile sequencer for the NxN output stationary array. 

// this block owns the timing, not the data. it omits a slice index 'k_idx' and the 
//feeder supplies the operand bytes MEM_LATENCY cycles later. 
//the tile tags travel thru delay lines of the same depth so that they arrive at the array boundry on the same 
//edge as the operands they tag. 