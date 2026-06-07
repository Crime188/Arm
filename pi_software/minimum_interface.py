import json
import websockets
import asyncio
import ssl


class Interface:
    def __init__(self, server_uri):
        """Initializes interface with relay server URI."""
        self.server_uri = server_uri
        self.websocket = None

    async def connect(self):
        """Establish persistent websocket connection with SSL fix."""

        ssl_context = ssl.SSLContext()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        while True:
            try:
                self.websocket = await websockets.connect(
                    self.server_uri,
                    ssl=ssl_context,
                    ping_interval=20,
                    ping_timeout=20
                )

                print("Connected to relay server.")
                return

            except Exception as e:
                print(f"Connection failed: {e}. Retrying in 3 seconds...")
                await asyncio.sleep(3)

    async def send_command(self, command: list):
        """
        Sends angles to robot:
        [base, secondary, tool, rotation]
        """

        if not self.websocket:
            print("WebSocket not connected.")
            return

        try:
            await self.websocket.send(
                json.dumps({"angles": command})
            )

        except Exception as e:
            print(f"Send failed: {e}")
            self.websocket = None  # force reconnect

    async def receive_data(self):
        """Receives data safely from websocket."""

        if not self.websocket:
            return None

        try:
            message = await self.websocket.recv()
            return json.loads(message)

        except Exception as e:
            print(f"Receive failed: {e}")
            self.websocket = None
            return None

    async def ensure_connection(self):
        """Auto-reconnect helper."""
        if not self.websocket:
            await self.connect()