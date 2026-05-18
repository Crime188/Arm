#include <Servo.h>
#include <AccelStepper.h>

/* ===================== SERVOS ===================== */
Servo servo1;
Servo servo2;
Servo servo3;

/* ===================== PINS ===================== */
const int SERVO1_PIN = 9;
const int SERVO2_PIN = 10;
const int SERVO3_PIN = 11;

// Stepper motor pins (4-wire)
const int STEP1_PIN = 4;
const int STEP2_PIN = 5;
const int STEP3_PIN = 6;
const int STEP4_PIN = 7;

/* ===================== SERVO STATE ===================== */
int angle1 = 115;
int angle2 = 160;
int angle3 = 0;

/* ===================== ACCELSTEPPER ===================== */
// FULL4WIRE mode for ULN2003 + 28BYJ-48 style motors
AccelStepper stepper(
  AccelStepper::FULL4WIRE,
  STEP1_PIN,
  STEP3_PIN,
  STEP2_PIN,
  STEP4_PIN
);

/* ===================== SETUP ===================== */
void setup() {
  Serial.begin(115200);

  /* ----- Attach servos ----- */
  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);
  servo3.attach(SERVO3_PIN);

  /* ----- Move servos to neutral ----- */
  moveServos(angle1, angle2, angle3);

  /* ----- Stepper configuration ----- */
  stepper.setMaxSpeed(1000);      // steps/sec
  stepper.setAcceleration(500);  // steps/sec^2
  stepper.setCurrentPosition(0);

  Serial.println("READY");
}

/* ===================== MAIN LOOP ===================== */
void loop() {

  // Non-blocking stepper update
  stepper.run();

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
  // servo1,servo2,servo3,stepper
  // Example:
  // 90,45,120,1000

  if (c1 == -1 || c2 == -1 || c3 == -1) {
    Serial.println("ERR: format must be s1,s2,s3,step");
    return;
  }

  int a1 = cmd.substring(0, c1).toInt();
  int a2 = cmd.substring(c1 + 1, c2).toInt();
  int a3 = cmd.substring(c2 + 1, c3).toInt();
  long stepTarget = cmd.substring(c3 + 1).toInt();

  /* ----- Clamp servo values ----- */
  a1 = constrain(a1, 0, 180);
  a2 = constrain(a2, 0, 180);
  a3 = constrain(a3, 0, 180);

  /* ----- Move servos ----- */
  moveServos(a1, a2, a3);

  /* ----- Move stepper (NON-BLOCKING) ----- */
  stepper.moveTo(stepTarget);

  /* ----- Status output ----- */
  Serial.print("OK ");
  Serial.print(a1);
  Serial.print(",");
  Serial.print(a2);
  Serial.print(",");
  Serial.print(a3);
  Serial.print(",");
  Serial.println(stepTarget);
}

/* ===================== SERVO CONTROL ===================== */
void moveServos(int a1, int a2, int a3) {

  angle1 = a1;
  angle2 = a2;
  angle3 = a3;

  servo1.write(angle1);
  servo2.write(angle2);
  servo3.write(angle3);
}