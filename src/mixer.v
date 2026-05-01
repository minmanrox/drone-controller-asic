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
    assign throttleSigned = {1'b0, throttle};
    
    assign motor1 = throttleSigned - pitchSigned + rollSigned - yawSigned;
    assign motor2 = throttleSigned - pitchSigned - rollSigned + yawSigned;
    assign motor3 = throttleSigned + pitchSigned - rollSigned - yawSigned;
    assign motor4 = throttleSigned + pitchSigned + rollSigned + yawSigned;
    
endmodule
