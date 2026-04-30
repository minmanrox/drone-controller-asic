`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
//
// Project      : Drone Flight Controller
// File         : mix_to_pwm_esc.v
// Author       : Kyle Minihan
// Created      : 02 October 2025
// Description  : Convert the output of the mixer module to a PWM signal, sent to
//                  the ESCs.
// 
//////////////////////////////////////////////////////////////////////////////////

`include "system_params.vh"

module mix_to_pwm (
    input clk,                    // 25 MHz
    input rst_n,
    input signed [9:0] motor_value, // Mixer value (-293 to +489 by observation)
    input arm,
    output reg pwm_out
);
    localparam int MAX_PULSE_WIDTH = $clog2(`PWM_MAX + 1);
    reg [$clog2(`PWM_PERIOD+1)-1:0] counter;

    // Use wire with assign for combinational logic
    wire [MAX_PULSE_WIDTH-1:0] pulse_width;
    wire signed [9:0] motor_value_clamped;

    assign motor_value_clamped =
        (motor_value < -10'sd200) ? -10'sd200 :
        (motor_value >  10'sd489) ?  10'sd489 :
                                motor_value;
    assign pulse_width = arm ? `PWM_MIN + ((motor_value_clamped + 200) * (`PWM_MAX-`PWM_MIN) / 1024) : `PWM_MIN;

    // Generate PWM by counting up to pulse_width
    always @(posedge clk) begin
        if (~rst_n) begin
            counter <= 0;
            pwm_out <= 0;
        end else begin
            if (counter < `PWM_PERIOD - 1)
                counter <= counter + 1;
            else
                counter <= 0;

            pwm_out <= (counter < pulse_width);
        end
    end

endmodule
