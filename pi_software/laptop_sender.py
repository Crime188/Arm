import asyncio
import websockets
import json
import pygame
import time

class LaptopSender:
    def __init__(self, server_uri):
        self.server_uri = server_uri
        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() == 0:
            raise Exception("No controller detected!")
        
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        print(f"Sending commands from: {self.joystick.get_name()}")
        
        # Moved state and logic from Pi to Laptop
        self.angles = [115, 160, 0, 0.0] 
        self.sensitivity = 0.5
        self.deadzone = 0.1
        self.limits = [180, 160, 180]

    def get_target_angles(self):
        """Processes joystick input and returns calculated angles."""
        pygame.event.pump()
        axes = [self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())]

        # 1. Update Servos (Indices 0, 1, 2) using Sticks (Axes 0, 1, 3)
        stick_map = {0: 0, 1: 1, 3: 2} 
        for axis_idx, angle_idx in stick_map.items():
            if len(axes) > axis_idx:
                val = axes[axis_idx]
                if abs(val) > self.deadzone:
                    self.angles[angle_idx] = max(0.0, min(self.limits[angle_idx], self.angles[angle_idx] + val * self.sensitivity))

        # 2. Update Stepper (Index 3) using Triggers (Axes 4 and 5)
        if len(axes) >= 6:
            lt = (axes[4] + 1) / 2 if axes[4] != 0 else 0
            rt = (axes[5] + 1) / 2 if axes[5] != 0 else 0
            trigger_combined = rt - lt 
            if abs(trigger_combined) > self.deadzone:
                self.angles[3] += trigger_combined

        return [int(a) for a in self.angles]

    async def stream_to_relay(self):
        print(f"Connecting to Oracle Relay at {self.server_uri}...")
        while True:
            try:
                async with websockets.connect(self.server_uri) as websocket:
                    print("Connected! Streaming joystick data...")
                    while True:
                        angles = self.get_target_angles()
                        await websocket.send(json.dumps({"angles": angles}))
                        await asyncio.sleep(0.02) # 50Hz update rate
            except Exception as e:
                print(f"Connection lost ({e}). Retrying in 3s...")
                await asyncio.sleep(3)

if __name__ == "__main__":
    with open("credentials.json", 'r') as f:
        creds = json.load(f)
    ORACLE_IP = creds.get("server_ip")
    ORACLE_PORT = creds.get("server_port")
    URI = f"ws://{ORACLE_IP}:{ORACLE_PORT}"

    sender = LaptopSender(URI)
    try:
        asyncio.run(sender.stream_to_relay())
    except KeyboardInterrupt:
        pygame.quit()