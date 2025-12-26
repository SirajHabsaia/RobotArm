#include "cartesian.h"
#include "config.h"
#include "kinematics.h"
#include <math.h>

float smooth(float t, float duration) {
    // Smoothstep function
    t /= duration;
    return duration * t * t * (3 - 2 * t);
}

void line_cartesian(float t) {
    t = smooth(t, trajectory_time);

        float line_coordinates[3];
        for (uint8_t i = 0; i < 3; i++) {
            line_coordinates[i] = line_initial[i] + t / trajectory_time * (line_goal[i] - line_initial[i]);
        }

    inverse_kinematics(line_coordinates[0], line_coordinates[1], line_coordinates[2]);

    for (uint8_t j = 0; j < N; j++) {
        target_angle_snap[j] = calculated_inverse[j];
    }
}

void circle_cartesian(float t) {
    if (t < circle_line_time) {
        // Approach linearly to start of circle
        line_cartesian(t * trajectory_time / circle_line_time);
        return;
    }

    t = smooth(t - circle_line_time, trajectory_time - circle_line_time);
    float x = center_x + radius * cos(2*PI*t / (trajectory_time - circle_line_time));
    float z = center_z + radius * sin(2*PI*t / (trajectory_time - circle_line_time));

    inverse_kinematics(x, 0, z);

    for (uint8_t j = 0; j < N; j++) {
        target_angle_snap[j] = calculated_inverse[j];
    }
}
