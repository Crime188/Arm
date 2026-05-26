#include <Servo.h>

/* ===================== SERVOS ===================== */
Servo servo1;
Servo servo2;
Servo servo3;
Servo servo4;

/* ===================== PINS ===================== */
const int SERVO1_PIN = 9;
const int SERVO2_PIN = 10;
const int SERVO3_PIN = 11;
const int SERVO4_PIN = 6;

/* ===================== SERVO STATE ===================== */
int angle1 = 140;
int angle2 = 145;
int angle3 = 23;
int angle4 = 90;

/* ===================== SETUP ===================== */
void setup() {
  Serial.begin(115200);

  /* ----- Attach servos ----- */
  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);
  servo3.attach(SERVO3_PIN);
  servo4.attach(SERVO4_PIN);

  /* ----- Move servos to neutral ----- */
  moveServos(angle1, angle2, angle3, angle4);

  Serial.println("READY");
}

/* ===================== MAIN LOOP ===================== */
void loop() {
  // Handle serial commands
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    parseCommand(cmd);
  }
}

/* ===================== COMMAND PARSER ===================== */
void parseCommand(String cmd) {

  cmd.trim();

  int c1 = cmd.indexOf(',');
  int c2 = cmd.indexOf(',', c1 + 1);
  int c3 = cmd.indexOf(',', c2 + 1);

  // Expected format:
  // servo1,servo2,servo3,servo4
  // Example:
  // 90,45,120,0

  if (c1 == -1 || c2 == -1 || c3 == -1) {
    Serial.println("ERR: format must be s1,s2,s3,s4");
    return;
  }

  int a1 = cmd.substring(0, c1).toInt();
  int a2 = cmd.substring(c1 + 1, c2).toInt();
  int a3 = cmd.substring(c2 + 1, c3).toInt();
  int a4 = cmd.substring(c3 + 1).toInt();

  /* ----- Clamp servo values ----- */
  a1 = constrain(a1, 0, 180);
  a2 = constrain(a2, 0, 150);
  a3 = constrain(a3, 0, 180);
  a4 = constrain(a4, 0, 180);

  /* ----- Move servos ----- */
  moveServos(a1, a2, a3, a4);

  /* ----- Status output ----- */
  Serial.print("OK ");
  Serial.print(a1);
  Serial.print(",");
  Serial.print(a2);
  Serial.print(",");
  Serial.print(a3);
  Serial.print(",");
  Serial.println(a4);
}

/* ===================== SERVO CONTROL ===================== */
void moveServos(int a1, int a2, int a3, int a4) {
  angle1 = a1;
  angle2 = a2;
  angle3 = a3;
  angle4 = a4;

  servo1.write(angle1);
  servo2.write(angle2);
  servo3.write(angle3);
  servo4.write(angle4);
}