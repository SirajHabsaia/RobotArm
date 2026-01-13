#ifndef CONTROL_H
#define CONTROL_H

#include <Arduino.h>

// Move a single stepper motor one step
void movestep(uint8_t joint, bool direction);

// Move Mx28 (gamma)
void move_gamma(float target_angle, int speed);

// Move Ax12 (gripper)
void move_gripper(float activation);

#endif // CONTROL_H
