`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
//
// Project      : Drone Flight Controller
// File         : mix_to_pwm_esc.v
// Author       : Kyle Minihan
// Created      : 02 October 2025
// Description  : Convert the output of the mixer module to a PWM signal, sent to
//                  the ESCs.
//                  Also includes logic for calibration sequence of the ESCs, first
//                  holding MIN for `CALIB_HOLD cycles, then holding MAX for
//                  `CALIB_HOLD cycles, and then proceeding to normal operation.
// 
//////////////////////////////////////////////////////////////////////////////////

`include "system_params.vh"

module mix_to_pwm (
    input clk,                    // 25 MHz
    input rst_n,
    input signed [9:0] motor_value, // Mixer value (-293 to +489 by observation)
    input arm,
    input reset_cal,
    output reg pwm_out,
    output reg calibration_complete
);
    localparam int MAX_PULSE_WIDTH = $clog2(`PWM_MAX + 1);
    reg [$clog2(`PWM_PERIOD+1)-1:0] counter;
    reg [$clog2(`CALIB_HOLD + 1)-1:0] calibration_counter;  // Counter for calibration timing
    reg [1:0] calibration_state;     // FSM for calibration state 0=MIN, 1=MAX, 2=normal
    
    // Calibration timing constants (for 125 MHz clock)
    localparam CAL_TIME = 30'd`CALIB_HOLD;

    // Use wire with assign for combinational logic
    wire [MAX_PULSE_WIDTH-1:0] pulse_width;
    wire signed [9:0] motor_value_clamped;

    assign motor_value_clamped =
        (motor_value < -10'sd200) ? -10'sd200 :
        (motor_value >  10'sd489) ?  10'sd489 :
                                motor_value;
    assign pulse_width = arm ? `PWM_MIN + ((motor_value_clamped + 200) * (`PWM_MAX-`PWM_MIN) / 1024) : `PWM_MIN;
    
    // Pulse MIN or MAX based on calibration state
    wire [MAX_PULSE_WIDTH-1:0] calibration_pulse_width;
    assign calibration_pulse_width = (calibration_state == 2'd0) ? `PWM_MAX : `PWM_MIN;
    
    // Select pulse width based on calibration state
    wire [MAX_PULSE_WIDTH-1:0] active_pulse_width;
    assign active_pulse_width = (calibration_state == 2'd2) ? pulse_width : calibration_pulse_width;
    
    // Calibration state machine
    always @(posedge clk) begin
        if (~rst_n) begin
            calibration_counter <= 0;
            calibration_state <= 2'd2;
        end else begin
            if (reset_cal == 1'b1) begin
                calibration_counter <= 0;
                calibration_state <= 0;
            end
            else if (calibration_state != 2'd2) begin
                if (calibration_counter < CAL_TIME - 1) begin
                    calibration_counter <= calibration_counter + 1;
                end else begin
                    calibration_counter <= 0;
                    calibration_state <= calibration_state + 1;
                end
            end
        end
    end
    
    always @(posedge clk) begin
        if (~rst_n)
            calibration_complete <= 1'b1;
        else
            calibration_complete <= (calibration_state == 2'd2) ? 1'b1 : 1'b0;
    end

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

            pwm_out <= (counter < active_pulse_width);
        end
    end

endmodule
