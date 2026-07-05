from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.models import ExperimentRequest
from backend.orchestrator import Orchestrator


ROOT_DIR = Path(__file__).resolve().parents[1]

app = FastAPI(title="Chaos Platform API", version="2.0")
app.mount(
    "/static",
    StaticFiles(directory=ROOT_DIR / "frontend" / "static"),
    name="static",
)

orchestrator = Orchestrator()
active_connections: List[WebSocket] = []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast(event: dict):
    stale_connections: list[WebSocket] = []
    for connection in active_connections:
        try:
            await connection.send_json(event)
        except RuntimeError:
            stale_connections.append(connection)

    for connection in stale_connections:
        active_connections.remove(connection)


@app.post("/api/experiments/run")
async def run_experiment(request: ExperimentRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        orchestrator.run_experiment,
        request.name,
        request.target,
        request.duration_override,
        request.dry_run,
    )
    return {
        "status": "accepted",
        "experiment": request.name,
        "target": request.target,
        "ws_endpoint": "/ws",
    }


@app.get("/api/experiments/history")
async def get_history(limit: int = 20):
    return orchestrator.history[-limit:]


@app.get("/api/hypothesis/status")
async def get_system_health():
    healthy = orchestrator.hypothesis.validate()
    return {
        "healthy": healthy,
        "checks": orchestrator.hypothesis.results,
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    template = ROOT_DIR / "frontend" / "templates" / "dashboard.html"
    return template.read_text(encoding="utf-8")


@app.post("/api/webhook/prometheus")
async def prometheus_webhook(alert: dict):
    return {"status": "received", "alert": alert}
