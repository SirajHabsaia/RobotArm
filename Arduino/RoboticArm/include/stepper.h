#ifndef STEPPER_H
#define STEPPER_H

#include <Arduino.h>

// Move a single stepper motor one step
void movestep(uint8_t joint, bool direction);

#endif // STEPPER_H
