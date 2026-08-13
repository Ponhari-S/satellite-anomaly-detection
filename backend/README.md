# OrbitGuard backend

Run from the repository root with Python 3.13:

```powershell
py -3.13 -m pip install -r backend/requirements.txt
py -3.13 -m uvicorn backend.main:app --reload
```

Endpoints:

- `GET /health` returns `{"status":"ok"}`.
- `POST /predict` accepts the 19 feature fields from `segments.csv`, applies the saved scaler and Logistic Regression model, and returns the anomaly class and class-1 probability.
- `WS /stream` replays the working `simulator/replay.py` source. It normalizes its current four fields into the raw telemetry API schema, scores each reading with temporary single-reading feature placeholders, and includes `prediction` and `probability` in each WebSocket message.
- `GET /results` returns the in-memory records scored during WebSocket streaming. They reset when the server restarts.

Interactive HTTP documentation is available at `http://127.0.0.1:8000/docs` while the server is running.
