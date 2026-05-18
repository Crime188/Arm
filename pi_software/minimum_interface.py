import json
import websockets
import asyncio

class interface:
    def __init__(self, server_uri):
        """Initializes the interface with the relay server URI."""
        self.server_uri = server_uri
        self.websocket = None

    async def connect(self):
        """Establishes a persistent websocket connection."""
        self.websocket = await websockets.connect(self.server_uri)

    async def send_command(self, command: list):
        """
        Sends a list of angles to the robot.
        command: List of angles [base, secondary, tool, stepper]
        """
        if self.websocket:
            await self.websocket.send(json.dumps({"angles": command}))

    async def receive_data(self):
        """Receives and parses data from the robot via the relay."""
        if self.websocket:
            message = await self.websocket.recv()
            return json.loads(message)
        return None
