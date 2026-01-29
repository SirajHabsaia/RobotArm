#include "control.h"
#include "config.h"

void movestep(uint8_t joint, bool direction) {
    bool hardware_direction = (inv_dir[joint]) ? !direction : direction;
    digitalWrite(DIR[joint], hardware_direction ? HIGH : LOW);
    digitalWrite(CLK[joint], HIGH);
    delayMicroseconds(4);
    digitalWrite(CLK[joint], LOW);
    current_step[joint] += direction ? 1 : -1;
    current_angle[joint] = (current_step[joint] * 360.0) / RESOLUTION[joint];
}

void toggle_motors(bool enable) {
    // First joint excluded
    for (uint8_t j = 1; j < N; j++) {
        digitalWrite(EN[j], !enable);
    }
}

void move_gamma(float target_angle, int speed) {
    int target_position = -map(target_angle, 0.0, 360.0, 0, 4095) + def_position_mx28;
    target_position = constrain(target_position, min_position_mx28, max_position_mx28);
    
    {
    unsigned char Position_H,Position_L, Speed_H, Speed_L;
    Position_H = (target_position >> 8) & 0xFF;
    Position_L = target_position & 0xFF;
    Speed_H = (speed >> 8) & 0xFF;
    Speed_L = speed & 0xFF;

    const unsigned int length = 11;
    unsigned char packet[length];

	unsigned char Checksum = (~(MX28_ID + 7 + 3 + 30 + Position_L + Position_H + Speed_L + Speed_H)) & 0xFF;

    packet[0] = 255;
    packet[1] = 255;
    packet[2] = MX28_ID;
    packet[3] = 7;
    packet[4] = 3;
    packet[5] = 30;
    packet[6] = Position_L;
    packet[7] = Position_H;
    packet[8] = Speed_L;
    packet[9] = Speed_H;
    packet[10] = Checksum;

    SERIAL_DXL.write(packet, length);
    current_gamma = target_angle;
}
}

void move_gripper(float activation) {
    int target_position = map(activation, 0.0, 100.0, min_position_ax12, max_position_ax12);
    
    {
    unsigned char Position_H,Position_L;
    Position_H = (target_position >> 8) & 0xFF;
    Position_L = target_position & 0xFF;

    const unsigned int length = 9;
    unsigned char packet[length];

	unsigned char Checksum = (~(AX12_ID + 5 + 3 + 30 + Position_L + Position_H)) & 0xFF;

    packet[0] = 255;
    packet[1] = 255;
    packet[2] = AX12_ID;
    packet[3] = 5;
    packet[4] = 3;
    packet[5] = 30;
    packet[6] = Position_L;
    packet[7] = Position_H;
    packet[8] = Checksum;

    SERIAL_DXL.write(packet, length);
    current_gripper = target_position;
}
}