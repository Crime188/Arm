import asyncio
import json
import pygame
import time
from minimum_interface import Interface

class LaptopSender:
    def __init__(self, server_uri):
        self.server_uri = server_uri
        self.interface = Interface(server_uri)
        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() == 0:
            raise Exception("No controller detected!")
        
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        print(f"Sending commands from: {self.joystick.get_name()}")
        
        # Moved state and logic from Pi to Laptop
        self.angles = [140, 145, 23, 90]
        self.sensitivity = 0.5
        self.deadzone = 0.1
        self.limits = [180, 150, 180, 180]
        self.saved_locations = {}       # Dictionary to store D-pad locations
        self.recall_target = None       # Target for smooth movement
        self.last_hat = (0, 0)          # Track last hat state for edge detection

    def get_target_angles(self):
        """Processes joystick input and returns calculated angles."""
        pygame.event.pump()
        axes = [self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())]
        buttons = [self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())]
        hats = [self.joystick.get_hat(i) for i in range(self.joystick.get_numhats())]

        stick_active = False # Manual input flag to override auto-move

        # 1. Update Servos (Indices 0, 1, 2) using Sticks (Axes 0, 1, 3)
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
            lt = (axes[4] + 1) / 2 if axes[4] != 0 else 0
            rt = (axes[5] + 1) / 2 if axes[5] != 0 else 0
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

        return [int(a) for a in self.angles]

    async def stream_to_relay(self):
        print(f"Connecting to Oracle Relay at {self.server_uri}...")
        while True:
            try:
                await self.interface.connect()
                print("Connected! Streaming joystick data...")
                while True:
                    angles = self.get_target_angles()
                    await self.interface.send_command(angles)
                    await asyncio.sleep(0.02) # 50Hz update rate
            except Exception as e:
                print(f"Connection lost ({e}). Retrying in 3s...")
                await asyncio.sleep(3)

    async def cleanup(self):
        """Resource cleanup and homing."""
        print("Homing servos before exit...")
        target_angles = [140, 145, 23, 90]
        steps = 25
        if self.interface.websocket:
            for i in range(1, steps + 1):
                interp = [int(s + (t - s) * (i / steps)) for s, t in zip(self.angles, target_angles)]
                try:
                    await self.interface.send_command(interp)
                    await asyncio.sleep(0.04)
                except Exception as e:
                    print(f"Cleanup error: {e}")
                    break
        pygame.quit()
        print("Cleanup complete.")

if __name__ == "__main__":
    with open("credentials.json", 'r') as f:
        creds = json.load(f)
    ORACLE_IP = creds.get("server_ip")
    ORACLE_PORT = creds.get("server_port")
    URI = f"wss://{ORACLE_IP}/arm/"

    sender = LaptopSender(URI)
    try:
        asyncio.run(sender.stream_to_relay())
    except KeyboardInterrupt:
        asyncio.run(sender.cleanup())