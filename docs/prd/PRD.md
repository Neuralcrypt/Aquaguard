# Product Requirements Document

**Product:** Smart Hostel Water Monitoring and Anomaly Detection System  
**Version:** 1.0 (prototype baseline)  
**Status:** Proposed / under development  
**Scope:** One room, one ESP32, one flow sensor

## Problem
The hostel faces water shortages and needs better visibility into room-level consumption and potentially wasteful flow. The prototype measures flow, stores readings, presents consumption, and creates investigation alerts.

## Goals
- Measure real water use using a calibrated physical sensor.
- Show daily, weekly, monthly and seasonal consumption.
- Let an authorized operator configure daily limits and continuous-flow duration.
- Flag threshold violations and unusual readings for human investigation.
- Demonstrate automated tests and a repeatable CI/CD pipeline.

## Users
- Hostel warden / project administrator: view readings, configure limits, investigate alerts.
- ESP32 device: submit sensor readings.

## MVP requirements
1. Accept and validate non-negative readings from the configured room/sensor.
2. Store readings and avoid duplicate `device_sequence` values.
3. Show summary cards, history chart, seasonal totals, settings and alert statuses.
4. Store separate Summer, Monsoon and Winter limits.
5. Create daily-limit alerts when total interval volume exceeds the configured limit.
6. Create a continuous-flow investigation alert when the configured rule is satisfied.
7. Expose a baseline anomaly-analysis endpoint and report insufficient data honestly.
8. Expose health checks and support Docker Compose.
9. Run automated backend, frontend and ML tests in CI.

## Out of scope
Multiple installed sensors, automatic shutoff valves, water billing, confirmed leak diagnosis, production authentication, mobile app, and forecasting without adequate history.

## Acceptance criteria
- A valid reading can be stored and later retrieved.
- Invalid negative values are rejected.
- Duplicate device sequence values are rejected.
- Room/season settings persist.
- Dashboard totals agree with stored interval volumes.
- Alerts can be moved between Pending, Investigating and Resolved.
- Test workflows execute and deployment health checks pass.
- Physical calibration error is measured and documented before accuracy claims.

## Assumptions and risks
The prototype has Wi-Fi and a reachable backend. Sensor calibration and voltage compatibility must be verified. Seasonal month mapping is provisional. ML results require real historical data and preferably labelled evaluation examples. Alerts do not prove a leak.
