#include "feedback.h"
#include "config.h"

void feedback(bool bypass_interval) {
    if (!bypass_interval && (!feedback_enabled || !currently_following_trajectory)) return;
    
    current_time_micros = micros();
    if (bypass_interval || current_time_micros - last_feedback_time >= feedback_interval) {
        last_feedback_time = current_time_micros;
        
        // d<time>t<theta>a<alpha>b<beta>h<gamma>g<gripper>
        if (time_feedback_enabled) {
            Serial.print("d");
            Serial.print((current_time_micros - trajectory_start_us)/1e6f, 3);
        }
        Serial.print("t");
        Serial.print(current_angle[0], 2);
        Serial.print("a");
        Serial.print(current_angle[1], 2);
        Serial.print("b");
        Serial.print(current_angle[2], 2);
        Serial.print("h");
        Serial.print(current_gamma, 1);
        Serial.print("g");
        Serial.println(current_gripper, 1);
    }
}
