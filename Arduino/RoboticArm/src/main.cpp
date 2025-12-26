#include <Arduino.h>

// Include all module headers
#include "config.h"
#include "stepper.h"
#include "kinematics.h"
#include "trajectory.h"
#include "cartesian.h"
#include "serial_commands.h"
#include "feedback.h"

void setup() {
    Serial.begin(115200);
    for (uint8_t j = 0; j < N; j++) {
        pinMode(CLK[j], OUTPUT);
        pinMode(DIR[j], OUTPUT);
    }
    
    Serial.println("Available commands:");
    Serial.println("Interpolation: it<theta>a<alpha>b<beta> or ix<x>y<y>z<z>");
    Serial.println("Line: lx<line_goal_x>y<line_goal_y>z<line_goal_z>");
    Serial.println("Circle: cr<radius>x<center_x>y<center_y>z<center_z>");
}

void loop() {
    readSerial();
    if (currently_interpolating) follow_trajectory(interpolation_trajectory);
    if (currently_drawing_circle) follow_trajectory(circle_cartesian);
    if (currently_drawing_line) follow_trajectory(line_cartesian);

    feedback();
}