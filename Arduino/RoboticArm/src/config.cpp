#include "config.h"

// ===========================
// Stepper CONFIGURATION
// ===========================
uint8_t CLK[N] = {8, 2, 5};
uint8_t DIR[N] = {9, 3, 6};
uint8_t EN[N] = {10, 4, 7};
uint8_t LS[N] = {11, 13 , 12}; bool inv_LS[N] = {false, true, true};
float RESOLUTION[N] = {8.f*400.f*4.f, 8.f*200.f*54.5f*1.011f, 8.f*200.f*54.5f*0.978f};
float max_speed[N] = {20., 15., 15.};
float reset_speed[N] = {5., 5., 5.};
float acceleration[N] = {60., 20., 20.};
bool inv_dir[N] = {false, true, false};

float L1 = 250.0;
float L2 = 200.0;
float L3 = 180.0;
float L4 = 36.0;
float h = 150.0;

// ===========================
// DXL CONFIGURATION
// ===========================
int min_position_ax12 = 0;
int max_position_ax12 = 200;
int min_position_mx28 = 50;
int def_position_mx28 = 1520;
int max_position_mx28 = 2900;

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
float current_gamma = 0.0;
float goal_mu = 0.0;
bool update_gripper = false;
float gamma_diff_threshold = 1.0;
float current_gripper = 0.0;
float goal_gripper = 0.0;

// ===========================
// HOME VARIABLES
// ===========================
bool homed[N] = {false, false, false};
bool homed_all = true;
unsigned long last_homing_step[N] = {0, 0, 0};
float homing_delay[N] = {2000, 2000, 2000};
bool inv_dir_homing[N] = {false, true, false};
float calibrated_angles[N] = {-4.5, -16.8-1.0, 45.8-2.0};

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
bool currently_following_planned = false;

unsigned long trajectory_check_interval = 50;
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

// ===========================
// LIST EXECUTION
// ===========================
bool executing_list = false;
Waypoint waypoint_buffer[MAX_WAYPOINTS];
uint8_t waypoint_count = 0;
uint8_t waypoint_index = 0;
bool done_waypoint = true;
bool paused_execution = false;

unsigned long segment_planned_time = 0;
unsigned long total_planned_time = 0;
bool must_execute_planned = false;
uint8_t current_segment = 0;