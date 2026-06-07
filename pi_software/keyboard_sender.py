import asyncio
import json
import pygame
import math
from minimum_interface import Interface


class KeyboardSender:
    def __init__(self, server_uri):
        self.server_uri = server_uri
        self.interface = Interface(server_uri)

        pygame.init()

        # Bigger window for visualization
        self.W, self.H = 600, 600
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("Robot Arm Control + Visualization")

        self.clock = pygame.time.Clock()

        # Joint state
        self.angles = [140, 145, 23, 90]
        self.sensitivity = 0.5
        self.limits = [180, 150, 180, 180]

        # Arm geometry (tweak for your robot proportions)
        self.lengths = [120, 100, 10, 0]

        self.font = pygame.font.SysFont("consolas", 18)

    # -------------------------
    # INPUT HANDLING
    # -------------------------
    def get_target_angles(self):
        pygame.event.pump()
        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            self.angles[0] = min(self.limits[0], self.angles[0] + self.sensitivity)
        if keys[pygame.K_RIGHT]:
            self.angles[0] = max(0.0, self.angles[0] - self.sensitivity)

        if keys[pygame.K_UP]:
            self.angles[1] = min(self.limits[1], self.angles[1] - self.sensitivity)
        if keys[pygame.K_DOWN]:
            self.angles[1] = max(0.0, self.angles[1] + self.sensitivity)

        if keys[pygame.K_w]:
            self.angles[2] = min(self.limits[2], self.angles[2] - self.sensitivity)
        if keys[pygame.K_s]:
            self.angles[2] = max(0.0, self.angles[2] + self.sensitivity)

        if keys[pygame.K_a]:
            self.angles[3] = max(0.0, self.angles[3] - self.sensitivity)
        if keys[pygame.K_d]:
            self.angles[3] = min(self.limits[3], self.angles[3] + self.sensitivity)

        return [int(a) for a in self.angles]

    # -------------------------
    # FORWARD KINEMATICS
    # -------------------------
    def _get_limit(self, i):
        """Return (min_angle, max_angle) for servo i."""
        lim = self.limits[i]
        return (0, lim) if isinstance(lim, (int, float)) else lim
    
    def clamp_angle(self, i, value):
        lo, hi = self._get_limit(i)
        return max(lo, min(hi, value))

    def compute_points(self):
        """
        Returns list of joint positions in screen space.
        Angles are clamped to per-servo limits before computing.
        """
        cx, cy = self.W // 2, self.H // 2 + 100

        x, y = cx, cy
        angle = 0
        angle_directions = [1, -1, -1, 1]
        angle_offsets = [0, 0, -112, 0]
        points = [(x, y)]

        for i in range(4):
            clamped = self.clamp_angle(i, self.angles[i])
            angle += (clamped + angle_offsets[i]) * angle_directions[i]
            rad = math.radians(angle)

            x += self.lengths[i] * math.cos(rad)
            y -= self.lengths[i] * math.sin(rad)

            points.append((x, y))

        return points

    # -------------------------
    # DRAWING
    # -------------------------
    def draw_arm(self):
        self.screen.fill((15, 15, 20))

        points = self.compute_points()

        # Draw links
        for i in range(len(points) - 1):
            pygame.draw.line(
                self.screen,
                (0, 200, 255),
                points[i],
                points[i + 1],
                6
            )

        # Draw joints
        for i, p in enumerate(points):
            pygame.draw.circle(self.screen, (255, 255, 255), (int(p[0]), int(p[1])), 8)
            pygame.draw.circle(self.screen, (0, 0, 0), (int(p[0]), int(p[1])), 8, 2)

        # HUD
        text = f"Angles: {[int(a) for a in self.angles]}"
        img = self.font.render(text, True, (200, 200, 200))
        self.screen.blit(img, (10, 10))

        pygame.display.flip()

    # -------------------------
    # NETWORK LOOP
    # -------------------------
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
                print("Connected! Focus window.")

                while True:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return

                    angles = self.get_target_angles()
                    await self.interface.send_command(angles)

                    # draw visual
                    self.draw_arm()

                    # limit CPU usage
                    self.clock.tick(60)
                    await asyncio.sleep(0.01)

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