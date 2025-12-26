#include "trajectory.h"
#include "config.h"
#include "stepper.h"
#include <math.h>

void begin_trajectory() {
    trajectory_start_us = micros();
    currently_following_trajectory = true;
}

void follow_trajectory(void (*trajectory_func)(float)) {
    current_time_micros = micros();
    if (!currently_following_trajectory) return;
    if (current_time_micros - last_trajectory_check_interval < trajectory_check_interval) return;
    last_trajectory_check_interval = current_time_micros;
    
    float t = (current_time_micros - trajectory_start_us) / 1e6f;
    
    if (t > trajectory_time) {
        currently_following_trajectory = false;
        currently_interpolating = false;
        currently_drawing_circle = false;
        currently_drawing_line = false;

        Serial.print("Completed at [");
        for (uint8_t j = 0; j < N; j++) {
            Serial.print(current_angle[j]);
            if (j < N - 1) Serial.print(", ");
        }
        Serial.println("]");

        return;
    }
    
    trajectory_func(t);
    
    for (uint8_t j = 0; j < N; j++) {
        difference_angle_trajectory[j] = target_angle_snap[j] - current_angle[j];

        if (abs(difference_angle_trajectory[j]) > (360.0 / RESOLUTION[j])) {
            movestep(j, (difference_angle_trajectory[j] > 0));
        }
    }
}

void calculate_interpolation() {
    // Get distances
    float distances[N];
    for (uint8_t j = 0; j < N; j++) {
        initial_angle[j] = current_angle[j];
        distances[j] = abs(target_angle_interpolation[j] - initial_angle[j]);
        sign_interpolation[j] = (target_angle_interpolation[j] - initial_angle[j]) >= 0.0;
    }
    
    // Calculate minimal times
    float min_times[N];
    for (uint8_t j = 0; j < N; j++) {
        float d = distances[j];
        float a = acceleration[j];
        float t;
        if (d < (max_speed[j] * max_speed[j]) / a) {
            t = 2 * sqrt(d / a);
        } else {
            t = (d / max_speed[j]) + (max_speed[j] / a);
        }
        min_times[j] = t;
    }
    
    // Synchronized time
    float T = 0.0;
    for (uint8_t j = 0; j < N; j++) {
        if (min_times[j] > T) {
            T = min_times[j];
        }
    }
    
    for (uint8_t j = 0; j < N; j++) {
        float d = distances[j];
        float a = acceleration[j];

        float delta = (a * T) * (a * T) - 4 * a * d;
        if (delta < 0) delta = 0.0;

        speed[j] = (a * T - sqrt(delta)) / 2.0;

        float t_a = speed[j] / a;
        float t_c = T - 2.0 * t_a;

        // Numerical safety clamping
        if (-1e-9 < t_c && t_c < 0) {
            t_c = 0.0;
        }
        if (-1e-9 < speed[j] && speed[j] < 0) {
            speed[j] = 0.0;
        }

        t_cru_s[j] = t_a;
        t_dec_s[j] = t_a + t_c;
        t_stp_s[j] = T;

        last_acceleration_angle[j] = initial_angle[j] + (sign_interpolation[j] ? 1 : -1) * (speed[j] * speed[j]) / (2.0 * a);
        last_cruising_angle[j] = last_acceleration_angle[j] + (sign_interpolation[j] ? 1 : -1) * speed[j] * t_c;
    }

    Serial.print("\nMoving from [");
    Serial.print(current_angle[0]);
    Serial.print(", ");
    Serial.print(current_angle[1]);
    Serial.print("] to [");
    Serial.print(target_angle_interpolation[0]);
    Serial.print(", ");
    Serial.print(target_angle_interpolation[1]);
    Serial.print("] in ");
    Serial.print(T, 4);
    Serial.println(" seconds.");
}

void interpolation_trajectory(float t) {
    for (uint8_t j = 0; j < N; j++) {
        bool sign = sign_interpolation[j];

        if (t < t_cru_s[j]) { // Acceleration phase
            target_angle_snap[j] = initial_angle[j] + (sign ? 1 : -1) * acceleration[j] * (t*t) / 2.0f;
        } else if (t < t_dec_s[j]) { // Cruising phase
            target_angle_snap[j] = last_acceleration_angle[j] + (sign ? 1 : -1) * speed[j] * (t - t_cru_s[j]);
        } else if (t <= t_stp_s[j]) { // Deceleration phase
            target_angle_snap[j] = last_cruising_angle[j] + (sign ? 1 : -1) * (speed[j] * (t - t_dec_s[j]) - (acceleration[j] * (t - t_dec_s[j]) * (t - t_dec_s[j])) / 2.0f);
        }
    }
}

void begin_interpolate() {
    calculate_interpolation();
    trajectory_time = t_stp_s[0]; // Same for all joints

    currently_interpolating = true;
    begin_trajectory();
}
