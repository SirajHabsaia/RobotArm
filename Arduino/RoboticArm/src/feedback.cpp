#include "feedback.h"
#include "config.h"

void feedback() {
    if (!feedback_enabled || !currently_following_trajectory) return;
    
    current_time_micros = micros();
    if (current_time_micros - last_feedback_time >= feedback_interval) {
        last_feedback_time = current_time_micros;
        
        // d<time>t<theta>a<alpha>b<beta>
        if (time_feedback_enabled) {
            Serial.print("d");
            Serial.print((current_time_micros - trajectory_start_us)/1e6f, 3);
        }
        Serial.print("t");
        Serial.print(current_angle[0], 2);
        Serial.print("a");
        Serial.print(current_angle[1], 2);
        Serial.print("b");
        Serial.println(current_angle[2], 2);
    }
}
