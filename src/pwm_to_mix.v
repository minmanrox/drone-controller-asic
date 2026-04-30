`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
//
// Project      : Drone Flight Controller
// File         : pwm_to_mix.v
// Author       : Kyle Minihan
// Created      : 02 October 2025
// Description  : Convert the input PWM signals from the receiver into unsigned values
//                  for throttle/pitch/roll/yaw
// 
//////////////////////////////////////////////////////////////////////////////////

`include "system_params.vh"

module pwm_to_mix(
    input clk,          // System clock
    input pwm_in,       // PWM signal from CRSF-PWM
    input rst_n,
    output reg [7:0] value // Normalized output
);
    reg [$clog2(`PWM_MAX+1)-1:0] high_counter;
    reg [$clog2(`PWM_MAX+1)-1:0] pulse_width;
    reg prev_pwm_in;
    reg [$clog2(`PWM_MAX-`PWM_MIN+1)-1:0] pw_shifted;

    always @(posedge clk) begin
        if (!rst_n) begin
            value <= 0;
            high_counter <= 0;
            pulse_width <= 0;
            prev_pwm_in <= 0;
            pw_shifted <= 0;
        end else begin
            prev_pwm_in <= pwm_in; // register for edge detection

            // Count HIGH time
            if (pwm_in)
                high_counter <= high_counter + 1;
            else
                high_counter <= 0;

            // Falling edge detector: previous=1, current=0
            if (prev_pwm_in & ~pwm_in) begin
                // clamp value to range
                if (high_counter <= `PWM_MIN)
                    pulse_width <= `PWM_MIN;
                else if (high_counter >= `PWM_MAX)
                    pulse_width <= `PWM_MAX;
                else
                    pulse_width <= high_counter;
            end

            // shift to 0
            pw_shifted <= (pulse_width > `PWM_MIN)
                            ? (pulse_width - `PWM_MIN)
                            : 0;

            // extract top 8 bits to avoid costly multiplication/division
            value <= pw_shifted[11:4];
        end
    end
endmodule
