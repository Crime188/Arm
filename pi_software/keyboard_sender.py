import asyncio
import json
import pygame
import time
from minimum_interface import Interface

class KeyboardSender:
    def __init__(self, server_uri):
        self.server_uri = server_uri
        self.interface = Interface(server_uri)
        pygame.init()
        
        # Pygame needs a window to capture keyboard events reliably
        self.screen = pygame.display.set_mode((400, 300))
        pygame.display.set_caption("Robot Keyboard Control")
        
        # State and logic
        self.angles = [140, 145, 23, 90]
        self.sensitivity = .5  # Degrees to move per update
        self.limits = [180, 150, 180, 180] # Limits for all 4 servos

    def get_target_angles(self):
        """Processes keyboard input and returns calculated angles."""
        pygame.event.pump()
        keys = pygame.key.get_pressed()
        # 1. Base (Index 0) using Left/Right Arrows
        if keys[pygame.K_LEFT]:
            self.angles[0] = min(self.limits[0], self.angles[0] + self.sensitivity)
        if keys[pygame.K_RIGHT]:
            self.angles[0] = max(0.0, self.angles[0] - self.sensitivity)

        # 2. Secondary (Index 1) using Up/Down Arrows
        if keys[pygame.K_UP]:
            self.angles[1] = min(self.limits[1], self.angles[1] - self.sensitivity)
        if keys[pygame.K_DOWN]:
            self.angles[1] = max(0.0, self.angles[1] + self.sensitivity)

        # 3. Tool (Index 2) using W/S Keys
        if keys[pygame.K_w]:
            self.angles[2] = min(self.limits[2], self.angles[2] - self.sensitivity)
        if keys[pygame.K_s]:
            self.angles[2] = max(0.0, self.angles[2] + self.sensitivity)

        # 4. Servo 4 (Index 3) using A/D Keys
        if keys[pygame.K_a]:
            self.angles[3] = max(0.0, self.angles[3] - self.sensitivity)
        if keys[pygame.K_d]:
            self.angles[3] = min(self.limits[3], self.angles[3] + self.sensitivity)

        return [int(a) for a in self.angles]

    async def stream_to_relay(self):
        print(f"Connecting to Oracle Relay at {self.server_uri}...")
        print("\nControl Mapping:")
        print("  Base:      Left / Right Arrows")
        print("  Secondary: Up / Down Arrows")
        print("  Tool:      W / S keys")
        print("  Servo 4:   A / D keys")
        
        while True:
            try:
                await self.interface.connect()
                print("Connected! Focus the 'Robot Keyboard Control' window to use keys.")
                while True:
                    # Maintain window event loop
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return

                    angles = self.get_target_angles()
                    await self.interface.send_command(angles)
                    await asyncio.sleep(0.02) # 50Hz update rate
            except Exception as e:
                print(f"Connection lost ({e}). Retrying in 3s...")
                await asyncio.sleep(3)

if __name__ == "__main__":
    with open("credentials.json", 'r') as f:
        creds = json.load(f)
    URI = f"wss://{creds.get('server_ip')}/arm/"

    sender = KeyboardSender(URI)
    try:
        asyncio.run(sender.stream_to_relay())
    except KeyboardInterrupt:
        pygame.quit()
