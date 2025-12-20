#include <Arduino.h>

int CLK1 = 2;
int CW1 = 3;
int EN1 = 4;
int capteur1 = 11;


void setup() {
  pinMode(CLK1, OUTPUT);
  pinMode(CW1, OUTPUT);
  pinMode(EN1, OUTPUT);
  pinMode(capteur1, INPUT);
  Serial.begin(9600);

  while (digitalRead(capteur1) == LOW) {
    digitalWrite(CLK1, HIGH);
    delayMicroseconds(500);
    digitalWrite(CLK1, LOW);
    delayMicroseconds(500);
  }
}

void loop() {
}
