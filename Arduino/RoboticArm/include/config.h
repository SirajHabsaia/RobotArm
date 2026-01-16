#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ===========================
// STEPPER CONFIGURATION
// ===========================
#define N 3  // number of joints

extern uint8_t CLK[N];
extern uint8_t DIR[N];
extern uint8_t LS[N]; extern bool inv_LS[N];
extern float RESOLUTION[N]; // steps per revolution
extern float max_speed[N]; // degrees per second
extern float reset_speed[N]; // degrees per second
extern float acceleration[N]; // degrees per second per second
extern bool inv_dir[N]; // invert direction flags

extern float L1;
extern float L2;
extern float L3;
extern float L3z;

// ===========================
// DXL CONFIGURATION
// ===========================
#define AX12_ID 5
#define MX28_ID 1
#define BAUDRATE 1000000ul
#define SERIAL_DXL Serial1

extern int min_position_ax12;
extern int max_position_ax12;
extern int min_position_mx28;
extern int def_position_mx28;
extern int max_position_mx28;

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
extern float current_gamma; // current gamma angle for gripper
extern float goal_mu; // goal mu angle for gripper
extern bool update_gripper; // flag to update gripper position
extern float gamma_diff_threshold; // threshold for gamma update

// ===========================
// HOME VARIABLES
// ===========================
extern bool homed[N]; // homing status
extern bool homed_all; // all joints homed status
extern unsigned long last_homing_step[N]; // last homing step time in us
extern float homing_delay[N]; // delay between homing steps in us
extern bool inv_dir_homing[N]; // invert homing direction flags
extern float calibrated_angles[N]; // calibrated angles after homing

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
extern bool currently_following_planned; // following planned trajectory flag

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

// ===========================
// LIST EXECUTION
// ===========================
#define AXES 5
#define MAX_WAYPOINTS 100
extern bool executing_list;
struct Waypoint {
    float coord[AXES];
};
extern Waypoint waypoint_buffer[];
extern uint8_t waypoint_count;
extern uint8_t waypoint_index;
extern bool done_waypoint;

extern unsigned long segment_planned_time; //us
extern unsigned long total_planned_time; //us
extern bool must_execute_planned; // start planned traj after interpolation

#endif // CONFIG_H
