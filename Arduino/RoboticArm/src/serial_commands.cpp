#include "serial_commands.h"
#include "config.h"
#include "kinematics.h"
#include "trajectory.h"
#include "cartesian.h"
#include <math.h>

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

                trajectory_time = length_line_JS / 50.0;

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
                trajectory_time = perimeter / 150.0;

                line_goal[0] = center_x + radius;
                line_goal[1] = 0.0;
                line_goal[2] = center_z;

                inverse_kinematics(line_goal[0], line_goal[1], line_goal[2]);

                length_line_JS = 0.0;
                for (uint8_t j = 0; j < N; j++) {
                    length_line_JS += (calculated_inverse[j] - current_angle[j]) * (calculated_inverse[j] - current_angle[j]);
                }
                length_line_JS = sqrt(length_line_JS);
                circle_line_time = length_line_JS / 50.0;

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
        } else if (c == 'd') { // Debug
            //print current angle position
            Serial.print("JS: [");
            for (uint8_t j = 0; j < N; j++) {
                Serial.print(current_angle[j], 2);
                if (j < N - 1) Serial.print(", ");
            }
            Serial.println("]");

            //print current cartesian position
            direct_kinematics(current_angle[0], current_angle[1], current_angle[2]);
            Serial.print("CS: [");
            Serial.print(calculated_direct[0], 2);
            Serial.print(", ");
            Serial.print(calculated_direct[1], 2);
            Serial.print(", ");
            Serial.print(calculated_direct[2], 2);
            Serial.println("]");

        }
    }
}
