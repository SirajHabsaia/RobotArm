#include "reset.h"
#include "control.h"
#include "config.h"
#include "trajectory.h"

void begin_reset() {
    for (uint8_t j = 0; j < N; j++) {
        homed[j] = false;
        homing_delay[j] = 1e6f * 360.f / (reset_speed[j] * RESOLUTION[j]); //us
    }
    homed_all = false;

    while (!homed_all) reset();

    for (uint8_t j = 0; j < N; j++) {
        current_angle[j] = calibrated_angles[j];
        current_step[j] = (int)((current_angle[j] * RESOLUTION[j]) / 360.0);
        target_angle_interpolation[j] = 0.0;
    }

    begin_interpolate();

}

void reset() {
    for (uint8_t j = 0; j < N; j++) {
        if (!homed[j]) {
            bool ls_state = digitalRead(LS[j]);
            if (inv_LS[j]) {
                ls_state = !ls_state;
            }
            if (!ls_state && (micros() - last_homing_step[j]) > homing_delay[j]) {
                movestep(j, (!homed[1] && j==2) ? inv_dir_homing[j] : !inv_dir_homing[j]);
                last_homing_step[j] = micros();
            } else if (ls_state) {
                homed[j] = true;
                current_step[j] = 0;
                current_angle[j] = 0.0;
            }
        }
    }

    homed_all = true;
    for (uint8_t i = 0; i < N; i++) {
        if (!homed[i]) {
            homed_all = false;
            break;
        }
    }
}