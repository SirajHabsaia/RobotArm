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
        if (homed[j]) continue;
        bool ls_state = digitalRead(LS[j]);
        if (inv_LS[j]) ls_state = !ls_state;
        if (ls_state) homed[j] = true;
    }

    for (uint8_t j = 0; j < N; j++) {
    if (micros() - last_homing_step[j] < homing_delay[j]) continue;

    if ((j==0 && !homed[0])) movestep(0, !inv_dir_homing[0]);
    if ((j==1 && !homed[1])) movestep(1, !inv_dir_homing[1]);
    if ((j==2 && (homed[1] && !homed[2]))) movestep(2, !inv_dir_homing[2]);
    if ((j==2 && (!homed[1] && homed[2]))) movestep(2, inv_dir_homing[2]);

    last_homing_step[j] = micros();
    }

    homed_all = true;
    for (uint8_t i = 0; i < N; i++) {
        if (!homed[i]) {
            homed_all = false;
            break;
        }
    }
}