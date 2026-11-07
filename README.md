# Smart Hostel Water Monitoring and Anomaly Detection System

A B.Tech major-project prototype for Room 101 using ESP32 + flow sensor, React, FastAPI, PostgreSQL, and a robust statistical anomaly baseline.

> **Prototype notice:** calibrate the physical sensor before relying on readings. The example calibration value is not universal. Alerts are investigation prompts, not proof of a leak. No automatic valve control is implemented. Simulated readings must be labelled as simulated in reports.

## Quick start (recommended: Docker Desktop)

1. Install Docker Desktop and ensure its engine is running.
2. In this directory, copy `.env.example` to `.env` and change `POSTGRES_PASSWORD` to a local password.
3. Run:

   ```powershell
   docker compose up --build
   ```

4. Open the dashboard at http://localhost:5173 and API docs at http://localhost:8000/docs.
5. Health check: http://localhost:8000/api/health.
6. Stop with `Ctrl+C`; to stop containers use `docker compose down`. To delete the local database volume too, use `docker compose down -v` (this permanently deletes stored data).

## Run without Docker (backend uses SQLite by default)

Backend, in one terminal:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend, in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000/api`. For direct backend mode, this is ready as-is. For a non-default backend URL, set `VITE_API_BASE_URL` before building/running Vite.

## API quick reference

- `GET /api/health`
- `GET /api/rooms/ROOM-101`
- `POST /api/readings`
- `GET /api/readings?room_id=ROOM-101&limit=100`
- `GET /api/summary?room_id=ROOM-101`
- `GET /api/settings?room_id=ROOM-101`
- `PUT /api/settings/Summer?room_id=ROOM-101`
- `PUT /api/sensors/SENSOR-101/calibration`
- `GET /api/alerts?room_id=ROOM-101`
- `PATCH /api/alerts/{alert_id}`
- `GET /api/seasonal-analysis?room_id=ROOM-101`
- `POST /api/anomaly-analysis?room_id=ROOM-101`

Example reading payload:

```json
{
  "room_id": "ROOM-101",
  "sensor_id": "SENSOR-101",
  "device_sequence": "esp32-1",
  "flow_rate_lpm": 1.2,
  "interval_volume_litres": 0.1
}
```

## Tests

Backend:

```powershell
cd backend
pip install -r requirements.txt
python -m pytest -v
```

ML tests (from repository root):

```powershell
pip install -r ml/requirements.txt
$env:PYTHONPATH = "ml"
python -m pytest ml/tests -v
```

Frontend:

```powershell
cd frontend
npm install
npm test
npm run lint
npm run build
```

## ESP32 firmware

See [`firmware/README.md`](firmware/README.md). Set Wi-Fi credentials and API host in firmware source locally; do not commit real credentials. Use a LAN-reachable host address, not `localhost`, because `localhost` on ESP32 refers to the ESP32 itself.

## Known prototype limitations

- The month-based season policy is a placeholder and should be confirmed with the university.
- The current continuous-flow detector uses incoming readings and a simple time-window check; test it against the sampling interval and adjust before claiming reliable leak detection.
- The anomaly detector is a robust median/MAD baseline, not a validated leak classifier.
- Firmware retry queue is not persistent; readings can be lost if a POST fails.
- The API does not implement authentication. Keep it on a trusted development network; add access control before deployment to real users.
- Schema creation is automatic for prototype convenience. Alembic migrations are scaffolded but not yet configured as the production migration path.
- CI workflows are starter templates and may need repository secrets, branch protection, GHCR permissions, and deployment host configuration before production use.

## Documentation

- `docs/prd/PRD.md`
- `docs/design/architecture.md`
- `docs/testing/test-plan.md`
- `docs/ci-cd/pipeline-design.md`
- `docs/development/tool-usage-log.md`
