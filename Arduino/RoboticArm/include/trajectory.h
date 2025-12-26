#ifndef TRAJECTORY_H
#define TRAJECTORY_H

// Start a trajectory
void begin_trajectory();

// Follow a trajectory using the provided function
void follow_trajectory(void (*trajectory_func)(float));

// Calculate interpolation parameters for smooth motion
void calculate_interpolation();

// Interpolation trajectory function
void interpolation_trajectory(float t);

// Begin interpolation movement
void begin_interpolate();

#endif // TRAJECTORY_H
