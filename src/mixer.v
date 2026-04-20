`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
//
// Project      : Drone Flight Controller
// File         : mixer.v
// Author       : Kyle Minihan
// Created      : 02 October 2025
// Description  : Map the throttle/yaw/pitch/roll (after converting from PWM to int
//                  to the power values for each motor).
//
// Notes: 
//    Motor 1 (Front Left, CCW): Throttle - Pitch + Roll - Yaw
//    Motor 2 (Front Right, CW): Throttle - Pitch - Roll + Yaw
//    Motor 3 (Rear Right, CCW): Throttle + Pitch - Roll - Yaw
//    Motor 4 (Rear Left,   CW): Throttle + Pitch + Roll + Yaw
// 
//////////////////////////////////////////////////////////////////////////////////

module mixer (
    input [7:0] throttle, yaw, pitch, roll,
    output signed [9:0] motor1, motor2, motor3, motor4
);
    wire signed [8:0] yawSigned, pitchSigned, rollSigned, throttleSigned;
    assign yawSigned = $signed(yaw - 97);
    assign pitchSigned = $signed(pitch - 97);
    assign rollSigned = $signed(roll - 97);
//    assign throttleSigned = $signed(throttle);
    assign throttleSigned = {1'b0, throttle};
    
    assign motor1 = throttleSigned - pitchSigned + rollSigned - yawSigned;
    assign motor2 = throttleSigned - pitchSigned - rollSigned + yawSigned;
    assign motor3 = throttleSigned + pitchSigned - rollSigned - yawSigned;
    assign motor4 = throttleSigned + pitchSigned + rollSigned + yawSigned;

/*
    // Step 1: Motor mixing (use larger bitwidths for intermediates)    
    wire [10:0] intermediateM1, intermediateM2, intermediateM3, intermediateM4;
    assign intermediateM1 = throttleSigned - pitchSigned + rollSigned - yawSigned;
    assign intermediateM2 = throttleSigned - pitchSigned - rollSigned + yawSigned;
    assign intermediateM3 = throttleSigned + pitchSigned - rollSigned - yawSigned;
    assign intermediateM4 = throttleSigned + pitchSigned + rollSigned + yawSigned;

    
    // Step 2: Find min
    wire signed [9:0] min_ab, min_cd, min_val;
    assign min_ab = (intermediateM1 < intermediateM2) ? intermediateM1 : intermediateM2;
    assign min_cd = (intermediateM3 < intermediateM4) ? intermediateM3 : intermediateM4;
    assign min_val = (min_ab < min_cd) ? min_ab : min_cd;
    
    wire signed [9:0] max_ab, max_cd, max_val;
    assign max_ab = (intermediateM1 > intermediateM2) ? intermediateM1 : intermediateM2;
    assign max_cd = (intermediateM3 > intermediateM4) ? intermediateM3 : intermediateM4;
    assign max_val = (max_ab > max_cd) ? max_ab : max_cd;
//    wire[9:0] min_val = min(intermediateM1, intermediateM2, intermediateM3, intermediateM4);
//    wire[9:0] max_val = max(intermediateM1, intermediateM2, intermediateM3, intermediateM4);
    
    // Step 3: Shift if needed
    wire[9:0] shift = (min_val < 0) ? -min_val : 0;
    wire[10:0] m1_shifted = intermediateM1 + shift;
    wire[10:0] m2_shifted = intermediateM2 + shift;
    wire[10:0] m3_shifted = intermediateM3 + shift;
    wire[10:0] m4_shifted = intermediateM4 + shift;
    
    // Step 4: Scale if max > 255
    wire[7:0] scale = (max_val + shift > 255) ? 255.0 / (max_val + shift) : 1.0;
    wire[7:0] m1_scaled = m1_shifted * scale;
    wire[7:0] m2_scaled = m2_shifted * scale;
    wire[7:0] m3_scaled = m3_shifted * scale;
    wire[7:0] m4_scaled = m4_shifted * scale;
    
    // Step 5: Clamp to [0,255]
    assign motor1 = (m1_scaled < 0) ?   0   :
                    (m1_scaled > 255) ? 255 :
                                    m1_scaled;
    assign motor2 = (m2_scaled < 0) ?   0   :
                    (m2_scaled > 255) ? 255 :
                                    m2_scaled;
    assign motor3 = (m3_scaled < 0) ?   0   :
                    (m3_scaled > 255) ? 255 :
                                    m3_scaled;
    assign motor4 = (m4_scaled < 0) ?   0   :
                    (m4_scaled > 255) ? 255 :
                                    m4_scaled;
    
*/
    
endmodule
