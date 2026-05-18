import asyncio
import json
import websockets

class OracleRelay:
    def __init__(self, host="0.0.0.0", port=8080):
        self.host = host
        self.port = port
        self.clients = set()

    async def handle_connection(self, websocket):
        """
        Acts as a simple bridge. Any message received from one client 
        (the laptop) is broadcast to all other clients (the Pi).
        """
        print(f"New connection from: {websocket.remote_address}")
        self.clients.add(websocket)
        try:
            async for message in websocket:
                # Relay the message to everyone else
                if len(self.clients) > 1:
                    await asyncio.gather(
                        *[client.send(message) for client in self.clients if client != websocket],
                        return_exceptions=True
                    )
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            print(f"Connection closed: {websocket.remote_address}")

    async def run(self):
        print(f"Oracle Relay active on {self.host}:{self.port}")
        async with websockets.serve(self.handle_connection, self.host, self.port):
            await asyncio.Future()  # Run forever

if __name__ == "__main__":
    with open("credentials.json", 'r') as f:
        creds = json.load(f)
    relay = OracleRelay(port = creds.get("server_port", 8080))
    try:
        asyncio.run(relay.run())
    except KeyboardInterrupt:
        print("Relay shutting down.")