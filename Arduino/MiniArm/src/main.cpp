#include <Arduino.h>

const uint8_t N = 2; // number of joints
uint8_t CLK[N] = {4, 2};
uint8_t DIR[N] = {5, 3};
int RESOLUTION[N] = {8*200, 8*200}; // steps per revolution
float max_speed[N] = {40., 40.}; // degrees per second
float acceleration[N] = {100., 100.}; // degrees per second per second
bool inv_dir[N] = {true, false}; // invert direction flags

unsigned long current_time_micros = 0;
unsigned long current_time_millis = 0; //unused still

float current_angle[N] = {0.0, 0.0}; // current angles in degrees
int current_step[N] = {0, 0}; // current step positions

float calculated_direct[N] = {0.0, 0.0}; // current cartesian positions (x,z)
float calculated_inverse[N] = {0.0, 0.0}; // current cartesian positions (x,z)


float target_angle_interpolation[N] = {0.0, 0.0}; // target angles in degrees for interpolation
float target_angle_snap[N] = {0.0, 0.0}; // target angles in degrees for trajectory


bool hardware_direction = true;
void movestep(uint8_t joint, bool direction) {
    hardware_direction = (inv_dir[joint]) ? !direction : direction;
    digitalWrite(DIR[joint], hardware_direction ? HIGH : LOW);
    digitalWrite(CLK[joint], HIGH);
    delayMicroseconds(4);
    digitalWrite(CLK[joint], LOW);
    current_step[joint] += direction ? 1 : -1;
    current_angle[joint] = (current_step[joint] * 360.0) / RESOLUTION[joint];
}

unsigned long trajectory_start_us = 0; //us
bool currently_following_trajectory = false;
bool currently_drawing_circle = false;
bool currently_drawing_line = false;

void begin_trajectory() {
    trajectory_start_us = micros(); //us
    currently_following_trajectory = true;
}

unsigned long trajectory_check_interval = 250; //us
unsigned long last_trajectory_check_interval = 0; //us
float difference_angle_trajectory[N] = {0.0, 0.0}; // between goal at t and current
float trajectory_time = 10.0;
bool currently_interpolating = false;

void follow_trajectory(void (*trajectory_func)(float)) {
    current_time_micros = micros();
    if (!currently_following_trajectory) return;
    if (current_time_micros - last_trajectory_check_interval < trajectory_check_interval) return;
    last_trajectory_check_interval = current_time_micros;
    
    float t = (current_time_micros - trajectory_start_us) / 1e6f; //s
    
    if (t > trajectory_time) {
        currently_following_trajectory = false;
        currently_interpolating = false;
        currently_drawing_circle = false;
        currently_drawing_line = false;

        Serial.print("Completed at [");
        Serial.print(current_angle[0]);
        Serial.print(", ");
        Serial.print(current_angle[1]);
        Serial.println("]");

        return;
    }
    
    trajectory_func(t);
    
    for (uint8_t j = 0; j < N; j++) {
        difference_angle_trajectory[j] = target_angle_snap[j] - current_angle[j];

        if (abs(difference_angle_trajectory[j]) > (360.0 / RESOLUTION[j])) {
            movestep(j, (difference_angle_trajectory[j] > 0));

            // if (j==0) Serial.print(difference_angle_trajectory[0] > 0 ? "+" : "-");
            // if (j==1) Serial.print(difference_angle_trajectory[1] > 0 ? ">" : "<");
        }
    }
}

float t_cru_s[N]; // cruising date
float t_dec_s[N]; // deceleration date
float t_stp_s[N]; // stopping date
float speed[N]; // peak speed

float initial_angle[N] = {0.0, 0.0};
float last_acceleration_angle[N] = {0.0, 0.0};
float last_cruising_angle[N] = {0.0, 0.0};
bool sign_interpolation[N] = {true, true};

void calculate_interpolation() {
    //get distances
    float distances[N];
    for (uint8_t j = 0; j < N; j++) {
        initial_angle[j] = current_angle[j];
        distances[j] = abs(target_angle_interpolation[j] - initial_angle[j]);
        sign_interpolation[j] = (target_angle_interpolation[j] - initial_angle[j]) >= 0.0;
    }
    
    //calculate minimal times
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
    //synchronized time
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
        if (delta < 0) delta = 0.0; //numerical safety

        // compute physically valid root
        speed[j] = (a * T - sqrt(delta)) / 2.0;

        float t_a = speed[j] / a;
        float t_c = T - 2.0 * t_a;

        // numerical safety clamping
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

        if (t < t_cru_s[j]) { //acceleration phase
            target_angle_snap[j] = initial_angle[j] + (sign ? 1 : -1) * acceleration[j] * (t*t) / 2.0f;
        } else if (t < t_dec_s[j]) { //cruising phase
            target_angle_snap[j] = last_acceleration_angle[j] + (sign ? 1 : -1) *speed[j] * (t - t_cru_s[j]);
        } else if (t <= t_stp_s[j]) { //deceleration phase
            target_angle_snap[j] = last_cruising_angle[j] + (sign ? 1 : -1) * (speed[j] * (t - t_dec_s[j]) - (acceleration[j] * (t - t_dec_s[j]) * (t - t_dec_s[j])) / 2.0f);
        }
    }
}

void begin_interpolate() {
    calculate_interpolation();
    trajectory_time = t_stp_s[0]; // same for all joints

    currently_interpolating = true;
    begin_trajectory();
}

void inverse_kinematics(float x, float z,float l1=250., float l2=200.) {
    float r = sqrt(x*x + z*z);
    float a = acos((-l2*l2 + l1*l1 + r*r)/(2*l1*r));
    float b = acos((l1*l1 + l2*l2 - r*r)/(2*l1*l2));
    float atn = atan2(z, x);

    calculated_inverse[0] = (PI - a -b - atn) * RAD_TO_DEG;
    calculated_inverse[1] = (PI/2 - a - atn) * RAD_TO_DEG;

}

void direct_kinematics(float alpha, float beta,float l1=250., float l2=200.) {
    float q1 = PI/2 - beta * DEG_TO_RAD;
    float q2 = -alpha * DEG_TO_RAD;

    calculated_direct[0] = l1 * cos(q1) + l2 * cos(q2);
    calculated_direct[1] = l1 * sin(q1) + l2 * sin(q2);
}


float smooth(float t, float duration) {
    // Smoothstep function
    t /= duration;
    return duration * t * t * (3 - 2 * t);
}

float line_goal_x = 0.0; float line_goal_y = 0.0; float length_line_JS = 0.0; float line_initial_x = 0.0; float line_initial_y = 0.0;
void line_cartesian(float t) {
    t = smooth(t, trajectory_time);
    float x = line_initial_x + t / trajectory_time * (line_goal_x - line_initial_x);
    float z = line_initial_y + t / trajectory_time * (line_goal_y - line_initial_y);

    inverse_kinematics(x, z);

    for (uint8_t j = 0; j < N; j++) target_angle_snap[j] = calculated_inverse[j];
}

float radius = 50; float center_x = 250; float center_y = 250; float perimeter = 0.0; float circle_line_time = 0.0;
void circle_cartesian(float t) {
    if (t< circle_line_time) {
        //approach linearly to start of circle
        line_cartesian(t * trajectory_time / circle_line_time);
        return;
    }

    t = smooth(t - circle_line_time, trajectory_time-circle_line_time);
    float x = center_x + radius * cos(2*PI*t / (trajectory_time - circle_line_time));
    float z = center_y + radius * sin(2*PI*t / (trajectory_time - circle_line_time));

    inverse_kinematics(x, z);

    for (uint8_t j = 0; j < N; j++) target_angle_snap[j] = calculated_inverse[j];
}

unsigned long serial_last_check = 0;
unsigned long serial_check_interval = 1000; //us
void readSerial() {
    current_time_micros = micros();
    if (current_time_micros - serial_last_check >= serial_check_interval && Serial.available()) {
        serial_last_check = current_time_micros;

        char c = Serial.read();

        if(c == 'i') { //interpolation
            String line = Serial.readStringUntil('\n');
            line.trim();

            // Parse format: a<angle1>b<angle2>
            int a_idx = line.indexOf('a');
            int b_idx = line.indexOf('b');
            
            if (a_idx != -1 && b_idx != -1 && b_idx > a_idx) {
                String angle1_str = line.substring(a_idx + 1, b_idx);
                String angle2_str = line.substring(b_idx + 1);
                
                target_angle_interpolation[0] = angle1_str.toFloat();
                target_angle_interpolation[1] = angle2_str.toFloat();
                
                begin_interpolate();
            } else {
                Serial.println("Invalid format. Use: a<angle1>b<angle2>");
            }
        } else if (c == 'c') { //circle
            String line = Serial.readStringUntil('\n');
            line.trim();

            // Parse format: r<radius>x<center_x>y<center_y>
            int r_idx = line.indexOf('r');
            int x_idx = line.indexOf('x');
            int y_idx = line.indexOf('y');
            
            if (r_idx != -1 && x_idx != -1 && y_idx != -1 && x_idx > r_idx && y_idx > x_idx) {
                String radius_str = line.substring(r_idx + 1, x_idx);
                String center_x_str = line.substring(x_idx + 1, y_idx);
                String center_y_str = line.substring(y_idx + 1);
                
                radius = radius_str.toFloat();
                center_x = center_x_str.toFloat();
                center_y = center_y_str.toFloat();

                perimeter = 2*PI*radius;
                trajectory_time = perimeter / 150.0;

                line_goal_x = center_x + radius;
                line_goal_y = center_y;
                inverse_kinematics(line_goal_x, line_goal_y);
                length_line_JS = sqrt( (calculated_inverse[0] - current_angle[0])*(calculated_inverse[0] - current_angle[0]) + (calculated_inverse[1] - current_angle[1])*(calculated_inverse[1] - current_angle[1]) );
                circle_line_time = length_line_JS / 50.0;
                direct_kinematics(current_angle[0], current_angle[1]);
                line_initial_x = calculated_direct[0];
                line_initial_y = calculated_direct[1];

                trajectory_time += circle_line_time;

                currently_drawing_circle = true;
                begin_trajectory();

            } else {
                Serial.println("Invalid format. Use: r<radius>x<center_x>y<center_y>");
            }
        } else if (c == 'l') { //line
            String line = Serial.readStringUntil('\n');
            line.trim();

            // Parse format: lx<line_goal_x>y<line_goal_y>
            int x_idx = line.indexOf('x');
            int y_idx = line.indexOf('y');
            
            if (x_idx != -1 && y_idx != -1 && y_idx > x_idx) {
                String line_goal_x_str = line.substring(x_idx + 1, y_idx);
                String line_goal_y_str = line.substring(y_idx + 1);
                
                line_goal_x = line_goal_x_str.toFloat();
                line_goal_y = line_goal_y_str.toFloat();

                inverse_kinematics(line_goal_x, line_goal_y);

                length_line_JS = sqrt( (calculated_inverse[0] - current_angle[0])*(calculated_inverse[0] - current_angle[0]) + (calculated_inverse[1] - current_angle[1])*(calculated_inverse[1] - current_angle[1]) );
                trajectory_time = length_line_JS / 30.0;

                direct_kinematics(current_angle[0], current_angle[1]);
                line_initial_x = calculated_direct[0];
                line_initial_y = calculated_direct[1];
                
                currently_drawing_line = true;
                begin_trajectory();
            } else {
                Serial.println("Invalid format. Use: a<angle1>b<angle2>");
            }
        } else if (c == 'd') { //debug
            inverse_kinematics(100,200);
            Serial.print("a = "); Serial.print(target_angle_snap[0], 2);
            Serial.print(", b = "); Serial.println(target_angle_snap[1], 2);
        }
    }

}

void setup() {
    Serial.begin(115200);
    for (uint8_t j = 0; j < N; j++) {
        pinMode(CLK[j], OUTPUT);
        pinMode(DIR[j], OUTPUT);
    }
    
    Serial.println("2-Joint Stepper Controller Ready");
    Serial.println("Send commands as: a<angle1>b<angle2>");

}

void loop() {
    readSerial();
    if (currently_interpolating) follow_trajectory(interpolation_trajectory);
    if (currently_drawing_circle) follow_trajectory(circle_cartesian);
    if (currently_drawing_line) follow_trajectory(line_cartesian);
}