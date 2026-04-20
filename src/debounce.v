`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
//
// Project      : Drone Flight Controller
// File         : debounce.v
// Author       : Kyle Minihan
// Created      : 06 November 2025
// Description  : Button debouncing module, taken from 
//                  https://www.fpga4student.com/2017/04/simple-debouncing-verilog-code-for.html
//////////////////////////////////////////////////////////////////////////////////


//fpga4student.com: FPGA projects, Verilog projects, VHDL projects
// Verilog code for button debouncing on FPGA
// debouncing module without creating another clock domain
// by using clock enable signal 
module debounce(input pb_1,clk,output pb_out);
wire slow_clk_en;
wire Q1,Q2,Q2_bar,Q0;
clock_enable u1(clk,slow_clk_en);

my_dff_en d0(clk,slow_clk_en,pb_1,Q0);


my_dff_en d1(clk,slow_clk_en,Q0,Q1);
my_dff_en d2(clk,slow_clk_en,Q1,Q2);
assign Q2_bar = ~Q2;
assign pb_out = Q1 & Q2_bar;
endmodule
/* verilator lint_off DECLFILENAME */
// Slow clock enable for debouncing button 
module clock_enable(input clk_25m,output slow_clk_en);
    reg [26:0]counter=0;
    always @(posedge clk_25m)
    begin
       counter <= (counter>=124999)?0:counter+1;
    end

    assign slow_clk_en = (counter == 124999)?1'b1:1'b0;
endmodule

// D-flip-flop with clock enable signal for debouncing module 
module my_dff_en(input DFF_CLOCK, clock_enable,D, output reg Q=0);
    always @ (posedge DFF_CLOCK) begin
  if(clock_enable==1) 
           Q <= D;
    end
endmodule 
/* verilator lint_on DECLFILENAME */

