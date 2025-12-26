#include "kinematics.h"
#include "config.h"
#include <math.h>

void inverse_kinematics(float x, float y, float z) {

    float theta = (x != 0) ? atan2(y, x) : (y > 0 ? 1 : -1) * PI/2;
    x = sqrt(x*x + y*y);

    //TODO: reduce gripper later

    float r = sqrt(x*x + z*z);
    float a = acos((-L2*L2 + L1*L1 + r*r)/(2*L1*r));
    float b = acos((L1*L1 + L2*L2 - r*r)/(2*L1*L2));
    float atn = atan2(z, x);

    calculated_inverse[0] = theta * RAD_TO_DEG;
    calculated_inverse[1] = (PI - a - b - atn) * RAD_TO_DEG;
    calculated_inverse[2] = (PI/2 - a - atn) * RAD_TO_DEG;
}

void direct_kinematics(float theta, float alpha, float beta) {
    //TODO: replace with L3 later
    float l3 = 0.0;
    float gamma = 0.0;

    float q1 = PI/2 - beta;
    float q2 = -alpha;
    float q3 = gamma - alpha;

    float x_plane = (
        L1 * cos(q1) +
        L2 * cos(q2) +
        l3 * cos(q3)
    );
    float z_plane = (
        L1 * sin(q1) +
        L2 * sin(q2) +
        l3 * sin(q3)
    );

    calculated_direct[0] = x_plane * cos(theta);
    calculated_direct[1] = x_plane * sin(theta);
    calculated_direct[2] = z_plane;
}
