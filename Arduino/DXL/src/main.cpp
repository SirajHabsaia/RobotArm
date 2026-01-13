
#include "Arduino.h"
#include "AX12A.h"

#define DirectionPin 	(50u)
#define BaudRate  		(1000000ul)
#define ID				(1u)

void setup()
{
	ax12a.begin(BaudRate, DirectionPin, &Serial2);
  Serial.begin(115200);
  //ax12a.move(ID, 3500);
}

void loop() {
  //check for incoming serial target position
  delay(1000);
  if (Serial.available()) {
    int target_position = Serial.parseInt();
    ax12a.moveSpeed(ID, target_position, 100);
  }
}