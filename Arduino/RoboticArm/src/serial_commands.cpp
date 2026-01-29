#include "serial_commands.h"
#include "config.h"
#include "kinematics.h"
#include "trajectory.h"
#include "cartesian.h"
#include <math.h>
#include <reset.h>
#include <control.h>

void readSerial() {
    current_time_micros = micros();
    if (current_time_micros - serial_last_check >= serial_check_interval && Serial.available()) {
        serial_last_check = current_time_micros;

        char c = Serial.read();

        if (c == 'i') { // Interpolation
            String line = Serial.readStringUntil('\n');
            line.trim();

            // Parse format: t<theta>a<alpha>b<beta>
            int t_idx = line.indexOf('t');
            int a_idx = line.indexOf('a');
            int b_idx = line.indexOf('b');
            
            if (t_idx != -1 && a_idx != -1 && b_idx != -1 && a_idx > t_idx && b_idx > a_idx) {
                String theta_str = line.substring(t_idx + 1, a_idx);
                String angle1_str = line.substring(a_idx + 1, b_idx);
                String angle2_str = line.substring(b_idx + 1);
                
                target_angle_interpolation[0] = theta_str.toFloat();
                target_angle_interpolation[1] = angle1_str.toFloat();
                target_angle_interpolation[2] = angle2_str.toFloat();
                
                //shortest theta path
                while (current_angle[0] - target_angle_interpolation[0] > 180.0) target_angle_interpolation[0] += 360.0;
                while (current_angle[0] - target_angle_interpolation[0] < -180.0) target_angle_interpolation[0] -= 360.0;

                begin_interpolate();
            
            } else {
                // Parse format: x<x>y<y>z<z>
                int x_idx = line.indexOf('x');
                int y_idx = line.indexOf('y');
                int z_idx = line.indexOf('z');

                if (x_idx != -1 && y_idx != -1 && z_idx != -1 && y_idx > x_idx && z_idx > y_idx) {
                    String x_str = line.substring(x_idx + 1, y_idx);
                    String y_str = line.substring(y_idx + 1, z_idx);
                    String z_str = line.substring(z_idx + 1);
                    
                    float x = x_str.toFloat();
                    float y = y_str.toFloat();
                    float z = z_str.toFloat();

                    inverse_kinematics(x, y, z);
                    
                    for (uint8_t j = 0; j < N; j++) {
                        target_angle_interpolation[j] = calculated_inverse[j];
                    }
                    
                    begin_interpolate();
                } else {
                    Serial.println("Invalid interpolation format. Use: it<theta>a<alpha>b<beta> or ix<x>y<y>z<z>");
                }
            }
        } else if (c == 'l') { // Line
            String line = Serial.readStringUntil('\n');
            line.trim();

            // Parse format: x<line_goal_x>y<line_goal_y>z<line_goal_z>
            int x_idx = line.indexOf('x');
            int y_idx = line.indexOf('y');
            int z_idx = line.indexOf('z');
            
            if (x_idx != -1 && y_idx != -1 && y_idx > x_idx && z_idx != -1 && z_idx > y_idx) {
                String line_goal_x_str = line.substring(x_idx + 1, y_idx);
                String line_goal_y_str = line.substring(y_idx + 1, z_idx);
                String line_goal_z_str = line.substring(z_idx + 1);

                line_goal[0] = line_goal_x_str.toFloat();
                line_goal[1] = line_goal_y_str.toFloat();
                line_goal[2] = line_goal_z_str.toFloat();

                inverse_kinematics(line_goal[0], line_goal[1], line_goal[2]);

                length_line_JS = 0.0;
                for (uint8_t j = 0; j < N; j++) {
                    length_line_JS += (calculated_inverse[j] - current_angle[j]) * (calculated_inverse[j] - current_angle[j]);
                }
                length_line_JS = sqrt(length_line_JS);

                trajectory_time = length_line_JS / 5.0;

                direct_kinematics(current_angle[0], current_angle[1], current_angle[2]);
                
                for (uint8_t i = 0; i < 3; i++) {
                    line_initial[i] = calculated_direct[i];
                }
                
                currently_drawing_line = true;
                begin_trajectory();
            } else {
                Serial.println("Invalid format. Use: a<angle1>b<angle2>");
            }
        } else if (c == 'c') { // Circle
            String line = Serial.readStringUntil('\n');
            line.trim();

            // Parse format: r<radius>x<center_x>z<center_z>
            int r_idx = line.indexOf('r');
            int x_idx = line.indexOf('x');
            int z_idx = line.indexOf('z');
            
            if (r_idx != -1 && x_idx != -1 && z_idx != -1 && x_idx > r_idx && z_idx > x_idx) {
                String radius_str = line.substring(r_idx + 1, x_idx);
                String center_x_str = line.substring(x_idx + 1, z_idx);
                String center_z_str = line.substring(z_idx + 1);
                
                radius = radius_str.toFloat();
                center_x = center_x_str.toFloat();
                center_z = center_z_str.toFloat();

                perimeter = 2*PI*radius;
                trajectory_time = perimeter / 20.0;

                line_goal[0] = center_x + radius;
                line_goal[1] = 0.0;
                line_goal[2] = center_z;

                inverse_kinematics(line_goal[0], line_goal[1], line_goal[2]);

                length_line_JS = 0.0;
                for (uint8_t j = 0; j < N; j++) {
                    length_line_JS += (calculated_inverse[j] - current_angle[j]) * (calculated_inverse[j] - current_angle[j]);
                }
                length_line_JS = sqrt(length_line_JS);
                circle_line_time = length_line_JS / 10.0;

                direct_kinematics(current_angle[0], current_angle[1], current_angle[2]);

                for (uint8_t j = 0; j < N; j++) {
                    line_initial[j] = calculated_direct[j];
                }

                trajectory_time += circle_line_time;

                currently_drawing_circle = true;
                begin_trajectory();

            } else {
                Serial.println("Invalid format. Use: r<radius>x<center_x>z<center_z>");
            }
        } else if (c == 'r') { // Reset
            String line = Serial.readStringUntil('\n');
            line.trim();
            
            if (line.length() > 0) {
                char dir = line.charAt(0);
                if (dir == 'l') {
                    inv_dir_homing[0] = false;
                    calibrated_angles[0] = -abs(calibrated_angles[0]);
                } else if (dir == 'r') {
                    inv_dir_homing[0] = true;
                    calibrated_angles[0] = abs(calibrated_angles[0]);
                } else {
                    Serial.println("Invalid homing direction. Use 'rr' for right or 'rl' for left.");
                    return;
                }
            } else {
                // Default to right if no direction specified
                inv_dir_homing[0] = false;
                calibrated_angles[0] = abs(calibrated_angles[0]);
            }
            
            currently_drawing_circle = false;
            currently_drawing_line = false;
            currently_interpolating = false;
            currently_following_trajectory = false;
            executing_list = false;
            currently_following_planned = false;
            must_execute_planned = false;
            Serial.println("Reset all movements.");
            begin_reset();
        } else if (c == 'h') { // gamma
            String line = Serial.readStringUntil('\n');
            line.trim();
            float gamma_angle = line.toFloat();
            update_gripper = false;
            goal_mu = 0.0;
            move_gamma(gamma_angle, 150);
        } else if (c == 'g') { // gripper
            String line = Serial.readStringUntil('\n');
            line.trim();
            float gripper_angle = line.toFloat();
            move_gripper(gripper_angle);
        } else if (c == 'm') { // mu
            String line = Serial.readStringUntil('\n');
            line.trim();
            goal_mu = line.toFloat();
            move_gamma(gamma_to_mu(goal_mu), 150);
            update_gripper = true;
        } else if (c == 'k') { // kinematics debugging
            goal_mu = 0.0; // Set a sample gamma angle for testing

            String line = Serial.readStringUntil('\n');
            line.trim();

            // Parse format: x<x>y<y>z<z>
            int x_idx = line.indexOf('x');
            int y_idx = line.indexOf('y');
            int z_idx = line.indexOf('z');

            if (x_idx != -1 && y_idx != -1 && z_idx != -1 && y_idx > x_idx && z_idx > y_idx) {
                String x_str = line.substring(x_idx + 1, y_idx);
                String y_str = line.substring(y_idx + 1, z_idx);
                String z_str = line.substring(z_idx + 1);
                
                float x = x_str.toFloat();
                float y = y_str.toFloat();
                float z = z_str.toFloat();

                inverse_kinematics(x, y, z);

                Serial.print("Inverse Kinematics JS: [");
                for (uint8_t j = 0; j < N; j++) {
                    Serial.print(calculated_inverse[j], 2);
                    if (j < N - 1) Serial.print(", ");
                }
                Serial.println("]");

                direct_kinematics(calculated_inverse[0], calculated_inverse[1], calculated_inverse[2]);
            } else {
                Serial.println("Invalid format. Use: x<x>y<y>z<z>");

            }
        } else if (c == 'n') { // receive list
            //read number of waypoints
            String line = Serial.readStringUntil(',');
            line.trim();
            waypoint_count = line.toInt();
            //read each waypoint in the format: x<x>y<y>z<z>m<mu>g<gripper>
            for (uint8_t i = 0; i < waypoint_count; i++) {
                String wp_line = Serial.readStringUntil(',');
                wp_line.trim();

                int x_idx = wp_line.indexOf('x');
                int y_idx = wp_line.indexOf('y');
                int z_idx = wp_line.indexOf('z');
                int m_idx = wp_line.indexOf('m');
                int g_idx = wp_line.indexOf('g');

                if (x_idx != -1 && y_idx != -1 && z_idx != -1 && m_idx != -1 && g_idx != -1 &&
                    y_idx > x_idx && z_idx > y_idx && m_idx > z_idx && g_idx > m_idx) {
                    
                    String x_str = wp_line.substring(x_idx + 1, y_idx);
                    String y_str = wp_line.substring(y_idx + 1, z_idx);
                    String z_str = wp_line.substring(z_idx + 1, m_idx);
                    String mu_str = wp_line.substring(m_idx + 1, g_idx);
                    String gripper_str = wp_line.substring(g_idx + 1);

                    waypoint_buffer[i].coord[0] = x_str.toFloat();
                    waypoint_buffer[i].coord[1] = y_str.toFloat();
                    waypoint_buffer[i].coord[2] = z_str.toFloat();
                    waypoint_buffer[i].coord[3] = mu_str.toFloat();
                    waypoint_buffer[i].coord[4] = gripper_str.toFloat();
                } else {
                    Serial.println("Invalid waypoint format. Use: x<x>y<y>z<z>m<mu>g<gripper>");
                    return; // Stop loading if any waypoint is invalid
                }
            }
            // Start execution after all waypoints loaded successfully
            executing_list = true;
            waypoint_index = 0;
            done_waypoint = true;
            Serial.print("n");
        } else if (c == 'w') { // receive planned waypoints
            // Format: wn<count>d<time_us>,t<theta>a<alpha>b<beta>m<mu>g<gripper>,t<theta>a<alpha>b<beta>m<mu>g<gripper>,...
            // Read count and time (up to first comma)
            String header = Serial.readStringUntil(',');
            header.trim();
            
            // Parse waypoint count
            int n_idx = header.indexOf('n');
            int d_idx = header.indexOf('d');
            
            if (n_idx == -1 || d_idx == -1 || d_idx <= n_idx) {
                Serial.println("Invalid format. Expected: n<count>d<time_us>");
                return;
            }
            
            String count_str = header.substring(n_idx + 1, d_idx);
            waypoint_count = count_str.toInt();
            
            String time_str = header.substring(d_idx + 1);
            segment_planned_time = time_str.toInt();
            total_planned_time = segment_planned_time * waypoint_count;
            
            // Parse each waypoint from serial stream
            for (uint8_t i = 0; i < waypoint_count; i++) {
                String wp_str = Serial.readStringUntil(',');
                wp_str.trim();
                
                // Parse t<theta>a<alpha>b<beta>m<mu>g<gripper>
                int t_idx = wp_str.indexOf('t');
                int a_idx = wp_str.indexOf('a');
                int b_idx = wp_str.indexOf('b');
                int m_idx = wp_str.indexOf('m');
                int g_idx = wp_str.indexOf('g');
                
                if (t_idx != -1 && a_idx != -1 && b_idx != -1 && m_idx != -1 && g_idx != -1 &&
                    a_idx > t_idx && b_idx > a_idx && m_idx > b_idx && g_idx > m_idx) {
                    
                    String theta_str = wp_str.substring(t_idx + 1, a_idx);
                    String alpha_str = wp_str.substring(a_idx + 1, b_idx);
                    String beta_str = wp_str.substring(b_idx + 1, m_idx);
                    String mu_str = wp_str.substring(m_idx + 1, g_idx);
                    String gripper_str = wp_str.substring(g_idx + 1);
                    
                    waypoint_buffer[i].coord[0] = theta_str.toFloat();
                    waypoint_buffer[i].coord[1] = alpha_str.toFloat();
                    waypoint_buffer[i].coord[2] = beta_str.toFloat();
                    waypoint_buffer[i].coord[3] = mu_str.toFloat();
                    waypoint_buffer[i].coord[4] = gripper_str.toFloat();
                } else {
                    Serial.println("Invalid waypoint format. Use: t<theta>a<alpha>b<beta>m<mu>g<gripper>");
                    return;
                }
            }

            // Start interpolation to first waypoint
            for (uint8_t j = 0; j < N; j++) {
                target_angle_interpolation[j] = waypoint_buffer[0].coord[j];
            }
            goal_mu = waypoint_buffer[0].coord[3];
            update_gripper = true;
            must_execute_planned = true;
            begin_interpolate();
        } else if (c == 's') { // Stop all movements
            currently_drawing_circle = false;
            currently_drawing_line = false;
            currently_interpolating = false;
            currently_following_trajectory = false;
            executing_list = false;
            currently_following_planned = false;
            must_execute_planned = false;
            paused_execution = false;
            Serial.println("Stopped all movements.");
        } else if (c == 'p') { // Pause list execution
            paused_execution = true;
        } else if (c == 'o') { // Resume list execution
            paused_execution = false;
        }
    }
}
