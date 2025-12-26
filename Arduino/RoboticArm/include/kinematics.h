#ifndef KINEMATICS_H
#define KINEMATICS_H

// Inverse kinematics: compute joint angles from cartesian position
void inverse_kinematics(float x, float y, float z);

// Direct kinematics: compute cartesian position from joint angles
void direct_kinematics(float theta, float alpha, float beta);

#endif // KINEMATICS_H
