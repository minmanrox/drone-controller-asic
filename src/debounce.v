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
module debounce(
    input clk,
    input rst_n,
    input pb_1,
    output pb_out
);
    wire slow_clk_en;
    wire Q1, Q2, Q2_bar, Q0;

    clock_enable u1(.clk(clk), .rst_n(rst_n), .slow_clk_en(slow_clk_en));
    my_dff_en d0(.DFF_CLOCK(clk), .rst_n(rst_n), .clock_enable(slow_clk_en), .D(pb_1), .Q(Q0));
    my_dff_en d1(.DFF_CLOCK(clk), .rst_n(rst_n), .clock_enable(slow_clk_en), .D(Q0), .Q(Q1));
    my_dff_en d2(.DFF_CLOCK(clk), .rst_n(rst_n), .clock_enable(slow_clk_en), .D(Q1), .Q(Q2));

    assign Q2_bar = ~Q2;
    assign pb_out = Q1 & Q2_bar;
endmodule

module my_dff_en(
    input DFF_CLOCK,
    input rst_n,
    input clock_enable,
    input D,
    output reg Q
);
    always @(posedge DFF_CLOCK) begin
        if (!rst_n)
            Q <= 0;
        else if (clock_enable)
            Q <= D;
    end
endmodule

module clock_enable(
    input clk,
    input rst_n,
    output slow_clk_en
);
    reg [26:0] counter;

    always @(posedge clk) begin
        if (!rst_n)
            counter <= 0;
        else
            counter <= (counter == 124999) ? 0 : counter + 1;
    end

    assign slow_clk_en = (counter == 124999);
endmodule

