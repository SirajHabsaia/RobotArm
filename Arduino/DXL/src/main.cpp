
#include "Arduino.h"
#include "AX12A.h"

#define DirectionPin 	(50u)
#define BaudRate  		(1000000ul)
#define ID				(5u)

void setup()
{
	ax12a.begin(BaudRate, DirectionPin, &Serial1);
  Serial.begin(115200);
  delay(100);
  ax12a.setCMargin(ID, 20, 20);
  delay(100);
  ax12a.setCSlope(ID, 128, 128);
  delay(100);
}

void loop() {
  //check for incoming serial target position
  delay(1000);
  if (Serial.available()) {
    int target_position = Serial.parseInt();
    ax12a.setMaxTorque(ID, 512);
    // ax12a.moveSpeed(ID, target_position, 100);
    ax12a.move(ID, target_position);
  }
}