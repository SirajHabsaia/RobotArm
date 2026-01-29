#include "trajectory.h"
#include "config.h"
#include "control.h"
#include "kinematics.h"
#include "feedback.h"
#include <math.h>

void begin_trajectory() {
    toggle_motors(true);

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
        if (currently_following_planned) Serial.println("D");
        currently_following_planned = false;
        if (executing_list) done_waypoint = true;
        if (must_execute_planned) {
            must_execute_planned = false;
            currently_following_planned = true;
            trajectory_time = total_planned_time / 1e6f;
            begin_trajectory();
        } else toggle_motors(false);
        feedback(true);
        return;
    }
    
    trajectory_func(t);
    
    for (uint8_t j = 0; j < N; j++) {
        difference_angle_trajectory[j] = target_angle_snap[j] - current_angle[j];
        uint8_t req_steps = round(abs(difference_angle_trajectory[j]) / (360.0 / RESOLUTION[j]));
        for (int step = 0; step < req_steps; step++) movestep(j, difference_angle_trajectory[j] > 0.0);
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

void execute_waypoint_list() {
    if (!executing_list) return;
    if (currently_following_trajectory) return;
    if (waypoint_index >= waypoint_count) {
        executing_list = false;
        waypoint_index = 0;
        return;
    }
    if (!done_waypoint || paused_execution) return;
    
    move_gripper(waypoint_buffer[waypoint_index].coord[4]);
    goal_mu = waypoint_buffer[waypoint_index].coord[3];
    update_gripper = true;

    inverse_kinematics(
        waypoint_buffer[waypoint_index].coord[0],
        waypoint_buffer[waypoint_index].coord[1],
        waypoint_buffer[waypoint_index].coord[2]
    );
    for (uint8_t j = 0; j < N; j++) {
        target_angle_interpolation[j] = calculated_inverse[j];
    }
    
    waypoint_index++;
    done_waypoint = false;
    begin_interpolate();
    //progress feedback
    Serial.print("n");
    Serial.println(waypoint_index-1);
}

void planned_trajectory(float t) {

    if (t >= total_planned_time / 1e6f) return; //should never be reached anyways
    // determine current waypoint segment
    uint8_t segment = max((int) (t / (segment_planned_time / 1e6f)), 1);
    if (current_segment != segment && waypoint_buffer[segment-1].coord[4] >= 0.0) move_gripper(waypoint_buffer[segment-1].coord[4]);
    current_segment = segment;
    float elapsed_in_segment = t - current_segment * (segment_planned_time / 1e6f);
    for (uint8_t j = 0; j < N; j++) {
        float start_angle = waypoint_buffer[current_segment-1].coord[j];
        float end_angle = waypoint_buffer[current_segment].coord[j];
        float segment_time = segment_planned_time / 1e6f;

        // Linear interpolation
        target_angle_snap[j] = start_angle + (end_angle - start_angle) * (elapsed_in_segment / segment_time);
    }
    goal_mu = waypoint_buffer[current_segment].coord[3];

}