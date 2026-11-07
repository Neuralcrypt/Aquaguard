# Architecture and data flow

```mermaid
flowchart TD
  A[Water flow] --> B[Flow sensor]
  B --> C[ESP32 firmware]
  C -->|HTTP JSON over Wi-Fi| D[FastAPI]
  D --> E[(PostgreSQL)]
  D --> F[Threshold alert rules]
  E --> G[Historical / seasonal analysis]
  E --> H[Robust anomaly baseline]
  F --> E
  H --> E
  D --> I[React dashboard]
  I --> J[Warden reviews alert]
```

## Services
- Frontend: React/Vite, served by Nginx in the container build.
- Backend: FastAPI, SQLAlchemy, Pydantic.
- Database: PostgreSQL in Compose; SQLite can be used for simple local backend development.
- Firmware: ESP32 pulse counter, flow conversion and HTTP posting.
- ML: median/MAD baseline and seasonal aggregation.

## Key data rules
- Store interval volume; do not sum repeated cumulative snapshots.
- Use stable room/sensor IDs and a unique device sequence where available.
- Store server timestamps as UTC-naive values in this prototype; the API normalizes timezone-aware timestamps to UTC.
- Confirm the month-to-season mapping with the institution.
- Alert means investigate, not confirmed leak.
