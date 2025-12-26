#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ===========================
// HARDWARE CONFIGURATION
// ===========================
#define N 3  // number of joints

extern uint8_t CLK[N];
extern uint8_t DIR[N];
extern int RESOLUTION[N]; // steps per revolution
extern float max_speed[N]; // degrees per second
extern float acceleration[N]; // degrees per second per second
extern bool inv_dir[N]; // invert direction flags

extern float L1;
extern float L2;
extern float L3;

// ===========================
// TIMING VARIABLES
// ===========================
extern unsigned long current_time_micros;
extern unsigned long current_time_millis;

// ===========================
// JOINT STATE
// ===========================
extern float current_angle[N]; // current angles in degrees
extern int current_step[N]; // current step positions

// ===========================
// KINEMATICS RESULTS
// ===========================
extern float calculated_direct[N]; // current cartesian positions (x,z)
extern float calculated_inverse[N]; // current joint angles from IK

// ===========================
// TRAJECTORY STATE
// ===========================
extern float target_angle_interpolation[N]; // target angles for interpolation
extern float target_angle_snap[N]; // target angles for trajectory

extern unsigned long trajectory_start_us;
extern bool currently_following_trajectory;
extern bool currently_drawing_circle;
extern bool currently_drawing_line;
extern bool currently_interpolating;

extern unsigned long trajectory_check_interval;
extern unsigned long last_trajectory_check_interval;
extern float difference_angle_trajectory[N];
extern float trajectory_time;

// ===========================
// INTERPOLATION PARAMETERS
// ===========================
extern float t_cru_s[N]; // cruising date
extern float t_dec_s[N]; // deceleration date
extern float t_stp_s[N]; // stopping date
extern float speed[N]; // peak speed

extern float initial_angle[N];
extern float last_acceleration_angle[N];
extern float last_cruising_angle[N];
extern bool sign_interpolation[N];

// ===========================
// CARTESIAN PATH PARAMETERS
// ===========================
extern float line_goal[N];
extern float line_initial[N];
extern float length_line_JS;

extern float radius;
extern float center_x;
extern float center_z;
extern float perimeter;
extern float circle_line_time;

// ===========================
// SERIAL COMMUNICATION
// ===========================
extern unsigned long serial_last_check;
extern unsigned long serial_check_interval;

// ===========================
// FEEDBACK SYSTEM
// ===========================
extern unsigned long last_feedback_time;
extern unsigned long feedback_interval;
extern bool feedback_enabled;
extern bool time_feedback_enabled;

#endif // CONFIG_H
