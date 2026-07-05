# Architecture

The project is split into a FastAPI backend, chaos injection modules, a lightweight dashboard frontend, automated tests, Grafana assets, and documentation.

- `backend/` contains API routes, orchestration, hypothesis checks, scheduling, notifications, persistence, and platform configuration.
- `modules/` contains one chaos injection module per failure mode.
- `frontend/` contains the Streamlit entrypoint plus the HTML/WebSocket dashboard.
- `tests/` is split into unit, integration, and fixture data.
- `grafana/` contains the chaos dashboard and datasource provisioning.
