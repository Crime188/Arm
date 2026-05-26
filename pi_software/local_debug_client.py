import cv2
import pygame
import json
import serial
import time
import sys

class LocalDebugClient:
    def __init__(self, serial_port='COM6', camera_index=0):
        """
        Initializes the local debug client.
        :param serial_port: The serial port for the Arduino (e.g., /dev/ttyACM0 or COM3).
        :param camera_index: The index of the USB camera.
        """
        # 1. Initialize Controller (Pygame)
        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() == 0:
            print("No controller detected!")
            self.joystick = None
        else:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Controller detected: {self.joystick.get_name()}")

        # 2. Initialize Serial connection to Arqqduino
        try:
            self.ser = serial.Serial(serial_port, 115200, timeout=0.01)
            time.sleep(2) # Give Arduino time to reset
            print(f"Connected to Arduino on {serial_port}")
        except Exception as e:
            print(f"Warning: Could not open serial port {serial_port}: {e}")
            self.ser = None

        # State for incremental control (modifier mode)
        self.angles = [140, 145, 23, 90] # 4 Servos
        self.sensitivity = .5           # Degrees to move per update at max deflection
        self.deadzone = 0.1              # Ignore small stick movements to prevent drift
        self.limits = [180, 150, 180, 180] # Limits for all 4 servos
        self.saved_locations = {}       # Dictionary to store D-pad locations
        self.recall_target = None       # Target for smooth movement
        self.last_hat = (0, 0)          # Track last hat state for edge detection
        # 3. Initialize Camera
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            print(f"Error: Could not open video device at index {camera_index}")
        else:
            print("Video capture initialized.")

    def get_controller_state(self):
        """Reads joystick axes and buttons and returns a dictionary."""
        pygame.event.pump()
        
        if not self.joystick:
            return {"axes": [], "buttons": [], "hats": []}

        state = {
            "axes": [round(self.joystick.get_axis(i), 2) for i in range(self.joystick.get_numaxes())],
            "buttons": [self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())],
            "hats": [self.joystick.get_hat(i) for i in range(self.joystick.get_numhats())]
        }
        return state

    def run(self):
        """Main loop for local control and video preview."""
        print("Starting Local Debug Mode. Press 'q' on the video window to quit.")
        
        try:
            while True:
                # 1. Handle Controller Inputs and Serial Output
                cmd_data = self.get_controller_state()
                if self.ser:
                    axes = cmd_data.get("axes", [])
                    buttons = cmd_data.get("buttons", [])
                    hats = cmd_data.get("hats", [])
                    
                    stick_active = False # Manual input flag to override auto-move

                    # 1. Update Servos (Indices 0, 1, 2) using Sticks (Axes 0, 1, 3)
                    # Mapping: Axis 0 (LX) -> Servo 1, Axis 1 (LY) -> Servo 2, Axis 3 (RY) -> Servo 3
                    stick_map = {0: 0, 1: 1, 3: 2} 
                    for axis_idx, angle_idx in stick_map.items():
                        if len(axes) > axis_idx:
                            val = axes[axis_idx]
                            if angle_idx == 0:  # Reverse base (bottom) servo
                                val = -val
                            if abs(val) > self.deadzone:
                                stick_active = True
                                self.angles[angle_idx] = max(0.0, min(self.limits[angle_idx], self.angles[angle_idx] + val * self.sensitivity))

                    # 2. Update Servo 4 (Index 3) using Triggers (Axes 4 and 5)
                    if len(axes) >= 6:
                        # Normalize triggers: -1.0 (unpressed) to 1.0 (pressed) maps to 0.0 to 1.0
                        # Note: We check axes[i] != 0 to handle Pygame's startup state where triggers stay at 0.0 until moved
                        lt = (axes[4] + 1) / 2 if axes[4] != 0 else 0
                        rt = (axes[5] + 1) / 2 if axes[5] != 0 else 0
                        
                        # Right trigger adds to position, Left trigger subtracts
                        trigger_combined = rt - lt 
                        if abs(trigger_combined) > self.deadzone:
                            stick_active = True
                            self.angles[3] = max(0.0, min(self.limits[3], self.angles[3] + trigger_combined * self.sensitivity))

                    # 3. D-pad Save/Recall logic
                    if hats and len(buttons) > 0:
                        hat = hats[0] # Typically D-pad
                        if hat != (0, 0) and hat != self.last_hat:
                            if buttons[0]: # Hold 'A' button (index 0) to save current position
                                self.saved_locations[hat] = list(self.angles)
                                print(f"Saved current location to D-pad {hat}: {self.angles}")
                            elif hat in self.saved_locations: # Press D-pad alone to recall position
                                self.recall_target = list(self.saved_locations[hat])
                                print(f"Moving to saved location {hat}: {self.recall_target}")
                        self.last_hat = hat

                    # 4. Handle smooth interpolation to target
                    if stick_active:
                        self.recall_target = None # Manual movement cancels recall
                    
                    if self.recall_target:
                        move_step = 1.0 # degrees per iteration (adjust for speed)
                        arrived = True
                        for i in range(len(self.angles)):
                            diff = self.recall_target[i] - self.angles[i]
                            if abs(diff) > move_step:
                                self.angles[i] += move_step if diff > 0 else -move_step
                                arrived = False
                            else:
                                self.angles[i] = self.recall_target[i]
                        
                        if arrived:
                            self.recall_target = None

                    s1, s2, s3, s4 = [int(a) for a in self.angles]
                    command_str = f"{s1},{s2},{s3},{s4}\n"
                    print(f"Serial Out: {command_str.strip()}")
                    try:
                        self.ser.write(command_str.encode('utf-8'))
                        # Read and discard any incoming data to prevent buffer overflow
                        if self.ser.in_waiting > 0:
                            self.ser.read_all()
                    except Exception as e:
                        print(f"Serial error: {e}")
                        self.ser = None # Attempt to mark as failed

                # 3. Exit condition
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                
                time.sleep(0.01) # Maintain loop timing

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Resource cleanup."""
        if self.ser:
            # Smoothly transition to the home position (115, 160, 0, 0)
            target_angles = [140, 145, 23, 90]
            steps = 25  # Number of steps for the transition
            for i in range(1, steps + 1):
                # Calculate intermediate angles based on current step
                interp = [int(s + (t - s) * (i / steps)) for s, t in zip(self.angles, target_angles)]
                cmd = f"{interp[0]},{interp[1]},{interp[2]},{interp[3]}\n"
                try:
                    self.ser.write(cmd.encode('utf-8'))
                    time.sleep(0.04)  # Small delay for smooth movement
                except Exception:
                    break
            self.ser.close()
        if self.cap: self.cap.release()
        cv2.destroyAllWindows()
        pygame.quit()

if __name__ == "__main__":
    # Adjust serial_port as needed ('COMx' for Windows, '/dev/ttyACM0' for Linux)
    client = LocalDebugClient(camera_index=0)
    client.run()
