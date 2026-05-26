import asyncio
import websockets
import json
import serial
import time
import sys

MAX_SPEED = 50.0 # degrees per second, for safety on the Pi side

class RemotePiClient:
    old_angles : list[float]
    def __init__(self, server_uri, serial_port='/dev/ttyACM0'):
        """
        Initializes the remote Pi client.
        :param server_uri: The websocket URI of the distant server (e.g., ws://192.168.1.100:8000).
        :param serial_port: Serial port for Arduino on Pi (usually /dev/ttyACM0).
        """
        self.server_uri = server_uri
        
        # 1. Initialize Serial connection to Arduino
        try:
            self.ser = serial.Serial(serial_port, 115200, timeout=0.01)
            time.sleep(2) # Give Arduino time to reset
            print(f"Connected to Arduino on {serial_port}")
        except Exception as e:
            print(f"Warning: Could not open serial port {serial_port}: {e}")
            self.ser = None
        self.old_angles = [140, 145, 23, 90] # assume we start at home position (4 Servos)
        self.last_update_time = time.time()


    def process_controller_data(self, data):
        """
        Receives processed angles and relays them directly to Arduino.
        Expects data format: {"angles": [s1, s2, s3, s4]}
        """
        angles = data.get("angles")
        if not angles or len(angles) < 4:
            return

        # Speed limit safety
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now
        max_step = MAX_SPEED * dt

        clamped_angles = []
        for i in range(len(angles)):
            target = float(angles[i])
            diff = target - self.old_angles[i]
            if abs(diff) > max_step:
                # Move only as far as the speed limit allows
                target = self.old_angles[i] + (max_step if diff > 0 else -max_step)
            clamped_angles.append(target)
        
        self.old_angles = clamped_angles

        # 3. Relay to Arduino
        if self.ser:
            s1, s2, s3, s4 = [int(a) for a in self.old_angles]
            command_str = f"{s1},{s2},{s3},{s4}\n"
            try:
                self.ser.write(command_str.encode('utf-8'))
                if self.ser.in_waiting > 0:
                    self.ser.read_all()
            except Exception as e:
                print(f"Serial error: {e}")

    async def run(self):
        """Main loop to maintain websocket connection and handle commands."""
        print(f"Connecting to server at {self.server_uri}...")
        
        while True:
            try:
                async with websockets.connect(self.server_uri) as websocket:
                    print("Connected to remote server.")
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            self.process_controller_data(data)
                        except json.JSONDecodeError:
                            print("Received non-JSON message")
            except Exception as e:
                print(f"Connection error: {e}. Retrying in 3 seconds...")
                await asyncio.sleep(3)

    def cleanup(self):
        """Resource cleanup and homing."""
        if self.ser:
            print("Homing servos before exit...")
            target_angles = [140, 145, 23, 90]
            steps = 25
            for i in range(1, steps + 1):
                interp = [int(s + (t - s) * (i / steps)) for s, t in zip(self.old_angles, target_angles)]
                cmd = f"{interp[0]},{interp[1]},{interp[2]},{interp[3]}\n"
                try:
                    self.ser.write(cmd.encode('utf-8'))
                    time.sleep(0.04)
                except:
                    break
            self.ser.close()
        print("Cleanup complete.")

if __name__ == "__main__":
    # Replace with Public IP
    json_path = "credentials.json"
    with open(json_path, 'r') as f:
        creds = json.load(f)

    SERVER_IP = creds.get("server_ip") 
    SERVER_PORT = creds.get("server_port")
    URI = f"ws://{SERVER_IP}:{SERVER_PORT}"

    client = RemotePiClient(server_uri=URI)
    
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        client.cleanup()
        loop.stop()