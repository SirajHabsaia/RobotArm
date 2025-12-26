#include "stepper.h"
#include "config.h"

void movestep(uint8_t joint, bool direction) {
    bool hardware_direction = (inv_dir[joint]) ? !direction : direction;
    digitalWrite(DIR[joint], hardware_direction ? HIGH : LOW);
    digitalWrite(CLK[joint], HIGH);
    delayMicroseconds(4);
    digitalWrite(CLK[joint], LOW);
    current_step[joint] += direction ? 1 : -1;
    current_angle[joint] = (current_step[joint] * 360.0) / RESOLUTION[joint];
}
