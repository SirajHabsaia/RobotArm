#include "config.h"

// ===========================
// HARDWARE CONFIGURATION
// ===========================
uint8_t CLK[N] = {6, 4, 2};
uint8_t DIR[N] = {7, 5, 3};
int RESOLUTION[N] = {8*200, 8*200, 8*200};
float max_speed[N] = {50., 15., 15.};
float acceleration[N] = {20., 10., 10.};
bool inv_dir[N] = {true, false, false};

float L1 = 250.0;
float L2 = 200.0;
float L3 = 150.0;

// ===========================
// TIMING VARIABLES
// ===========================
unsigned long current_time_micros = 0;
unsigned long current_time_millis = 0;

// ===========================
// JOINT STATE
// ===========================
float current_angle[N] = {0.0, 0.0, 0.0};
int current_step[N] = {0, 0, 0};

// ===========================
// KINEMATICS RESULTS
// ===========================
float calculated_direct[N] = {0.0, 0.0, 0.0};
float calculated_inverse[N] = {0.0, 0.0, 0.0};

// ===========================
// TRAJECTORY STATE
// ===========================
float target_angle_interpolation[N] = {0.0, 0.0, 0.0};
float target_angle_snap[N] = {0.0, 0.0, 0.0};

unsigned long trajectory_start_us = 0;
bool currently_following_trajectory = false;
bool currently_drawing_circle = false;
bool currently_drawing_line = false;
bool currently_interpolating = false;

unsigned long trajectory_check_interval = 250;
unsigned long last_trajectory_check_interval = 0;
float difference_angle_trajectory[N] = {0.0, 0.0, 0.0};
float trajectory_time = 10.0;

// ===========================
// INTERPOLATION PARAMETERS
// ===========================
float t_cru_s[N];
float t_dec_s[N];
float t_stp_s[N];
float speed[N];

float initial_angle[N] = {0.0, 0.0, 0.0};
float last_acceleration_angle[N] = {0.0, 0.0, 0.0};
float last_cruising_angle[N] = {0.0, 0.0, 0.0};
bool sign_interpolation[N] = {true, true, true};

// ===========================
// CARTESIAN PATH PARAMETERS
// ===========================
float line_goal[N] = {0.0, 0.0, 0.0};
float line_initial[N] = {0.0, 0.0, 0.0};
float length_line_JS = 0.0;

float radius = 50;
float center_x = 250;
float center_z = 250;
float perimeter = 0.0;
float circle_line_time = 0.0;

// ===========================
// SERIAL COMMUNICATION
// ===========================
unsigned long serial_last_check = 0;
unsigned long serial_check_interval = 1000;

// ===========================
// FEEDBACK SYSTEM
// ===========================
unsigned long last_feedback_time = 0;
unsigned long feedback_interval = 50e3;
bool feedback_enabled = true;
bool time_feedback_enabled = true;
