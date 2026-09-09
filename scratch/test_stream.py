import asyncio
import json
import websockets
import time

async def test_stream():
    url = "ws://127.0.0.1:8000/stream"
    print("Connecting to", url)
    async with websockets.connect(url) as ws:
        for i in range(15):
            msg = await ws.recv()
            data = json.loads(msg)
            assert "channel" in data, "Missing channel"
            assert "prediction" in data, "Missing prediction"
            assert "probability" in data, "Missing probability"
            assert "features" in data, "Missing features"
            assert len(data["features"]) == 19, f"Expected 19 features, got {len(data['features'])}"
            print(f"Frame {i+1}: {data['channel']} | val={data['value']:.4e} | pred={data['prediction']} | prob={data['probability']:.3f} | features={len(data['features'])}")
    print("All 15 frames successfully received and verified!")

if __name__ == "__main__":
    asyncio.run(test_stream())
