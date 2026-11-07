# Test Plan

## Methods and tools
- Unit: pytest (backend and ML), Vitest/Testing Library (frontend).
- API/integration: FastAPI TestClient/HTTPX, PostgreSQL integration tests, Postman or Swagger UI for manual checks.
- System/E2E: Playwright (add browser workflow tests as the UI stabilizes).
- Hardware: Arduino Serial Monitor, measuring jug, stopwatch, multimeter; compare known volume with sensor output.
- Security: Dependabot, GitHub secret scanning where available, Trivy image scan.
- CI/CD: GitHub Actions workflow logs and deployment smoke tests.

## Test cases (expected results; fill actual result after execution)
| ID | Scenario | Expected result | Evidence |
|---|---|---|---|
| T-01 | API health | HTTP 200 and healthy status | response/log |
| T-02 | Valid reading | Stored and returned | API/database test |
| T-03 | Negative volume | HTTP 422 | test output |
| T-04 | Duplicate device sequence | HTTP 409 | test output |
| T-05 | Setting update | New setting persists | API test |
| T-06 | Daily threshold crossed | One alert for day/event | integration test |
| T-07 | Alert status update | Status persists | API test |
| T-08 | Sensor calibration | New factor stored; history unchanged | test evidence |
| T-09 | Seasonal analysis | Totals grouped per documented policy | test output |
| T-10 | Insufficient ML data | Clear insufficient-data result | test output |
| T-11 | Sensor accuracy | Error calculated against known volume | lab record |
| T-12 | Wi-Fi interruption | Reconnect behaviour documented; missing intervals identified | serial log |
| T-13 | Container deployment | API health and frontend load | screenshot/log |
| T-14 | CI failure gate | Intentionally failing test fails workflow | Actions run |

Record actual result, date, environment, commit SHA, tester and evidence link for each run. Never pre-fill pass results without running the test.
