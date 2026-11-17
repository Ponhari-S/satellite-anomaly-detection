"""
WebSocket test client for the current backend.

Connects to the backend's /stream endpoint (defined in backend/main.py)
and prints each live reading along with its model prediction — this is
what you'll run during the demo to show the mentor the full pipeline
working: simulator -> backend -> feature extraction -> model -> result.

Run this from the project root, in a SEPARATE terminal from the one
running uvicorn:
    pip install websockets
    python stream_test_client.py

Make sure the backend is already running first:
    uvicorn backend.main:app --reload
"""

import asyncio
import json
import websockets

URL = "ws://127.0.0.1:8000/stream"


async def watch_stream():
    print(f"Connecting to {URL}\n")
    async with websockets.connect(URL) as ws:
        count = 0
        try:
            async for message in ws:
                data = json.loads(message)
                count += 1

                if "error" in data:
                    print("Error from server:", data["error"])
                    break

                flag = "ANOMALY" if data.get("anomaly") == 1 else "normal "
                pred = "ANOMALY" if data.get("prediction") == 1 else "normal "
                prob = data.get("probability", 0.0)

                print(f"#{count:4d}  [{data['timestamp']}]  {data['channel']}  "
                      f"value={data['value']:.4e}  true={flag}  "
                      f"predicted={pred}  probability={prob:.3f}")

        except websockets.exceptions.ConnectionClosed:
            print("\nStream ended (connection closed by server).")

        print(f"\nTotal readings received: {count}")


if __name__ == "__main__":
    asyncio.run(watch_stream())