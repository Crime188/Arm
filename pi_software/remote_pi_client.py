import asyncio
import websockets
import json
import serial
import time
import ssl

MAX_SPEED = 50.0  # degrees per second, safety limit


class RemotePiClient:
    old_angles: list[float]

    def __init__(self, server_uri, serial_port='/dev/ttyACM0'):
        self.server_uri = server_uri
        self.serial_port = serial_port

        self.ser = None
        self.last_serial_retry = 0

        self.old_angles = [140, 145, 23, 90]
        self.last_update_time = time.time()

        self.connect_serial()

    def connect_serial(self):
        """Connect to Arduino over serial"""
        self.last_serial_retry = time.time()

        try:
            self.ser = serial.Serial(self.serial_port, 115200, timeout=0.01)
            time.sleep(2)
            print(f"Connected to Arduino on {self.serial_port}")
        except Exception as e:
            print(f"Warning: serial connection failed: {e}")
            self.ser = None

    def process_controller_data(self, data):
        """
        Expected format:
        {"angles": [s1, s2, s3, s4]}
        """

        angles = data.get("angles")
        if not angles or len(angles) < 4:
            return

        now = time.time()
        dt = now - self.last_update_time
        if dt > 0.05:   # treat anything larger than 50ms as 50ms
            dt = 0.05
        self.last_update_time = now
        
        max_step = MAX_SPEED * dt

        clamped = []

        for i in range(4):
            target = float(angles[i])
            diff = target - self.old_angles[i]

            if abs(diff) > max_step:
                target = self.old_angles[i] + (max_step if diff > 0 else -max_step)

            clamped.append(target)

        self.old_angles = clamped

        # reconnect serial if needed
        if not self.ser and (time.time() - self.last_serial_retry > 5.0):
            print("Reconnecting serial...")
            self.connect_serial()

        # send to Arduino
        if self.ser:
            try:
                s1, s2, s3, s4 = [int(a) for a in self.old_angles]
                cmd = f"{s1},{s2},{s3},{s4}\n"

                self.ser.write(cmd.encode("utf-8"))

                if self.ser.in_waiting > 0:
                    self.ser.read_all()

            except Exception as e:
                print(f"Serial write error: {e}")
                self.ser = None

    async def run(self):
        """Main websocket loop"""

        print(f"Connecting to server at {self.server_uri}...")

        # 🔥 IMPORTANT: allow self-signed SSL (your current setup)
        ssl_context = ssl.SSLContext()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        while True:
            try:
                async with websockets.connect(
                    self.server_uri,
                    ssl=ssl_context,
                    ping_interval=20,
                    ping_timeout=20
                ) as websocket:

                    print("Connected to server.")

                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            self.process_controller_data(data)

                        except json.JSONDecodeError:
                            print("Invalid JSON received")

            except Exception as e:
                print(f"Connection error: {e}. Retrying in 3 seconds...")
                await asyncio.sleep(3)

    def cleanup(self):
        """Homing + cleanup"""

        if self.ser:
            print("Homing servos...")

            target = [140, 145, 23, 90]
            steps = 25

            for i in range(1, steps + 1):
                interp = [
                    int(s + (t - s) * (i / steps))
                    for s, t in zip(self.old_angles, target)
                ]

                cmd = f"{interp[0]},{interp[1]},{interp[2]},{interp[3]}\n"

                try:
                    self.ser.write(cmd.encode("utf-8"))
                    time.sleep(0.04)
                except:
                    break

            self.ser.close()

        print("Cleanup complete.")


# =========================
# MAIN ENTRY POINT
# =========================
if __name__ == "__main__":
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(BASE_DIR, "credentials.json")
    with open(json_path, "r") as f:
        creds = json.load(f)

    SERVER_IP = creds.get("server_ip")

    # 🔥 MUST include /oracle/
    URI = f"wss://{SERVER_IP}/arm/"

    client = RemotePiClient(server_uri=URI)

    try:
        asyncio.run(client.run())

    except KeyboardInterrupt:
        print("\nShutting down...")

    finally:
        client.cleanup()