#ifndef CARTESIAN_H
#define CARTESIAN_H

// Smoothstep interpolation function
float smooth(float t, float duration);

// Line trajectory in cartesian space
void line_cartesian(float t);

// Circle trajectory in cartesian space
void circle_cartesian(float t);

#endif // CARTESIAN_H
