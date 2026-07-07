from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.models import ExperimentRequest
from backend.orchestrator import Orchestrator

try:
    from backend.k8s_agent_client import ChaosAgentClient
    k8s_client = ChaosAgentClient()
except ImportError:
    k8s_client = None


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
    await websocket.send_json({"type": "connected", "message": "Connected to chaos event stream"})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast(event: dict):
    stale_connections: list[WebSocket] = []
    for connection in active_connections:
        try:
            await connection.send_json(event)
        except RuntimeError:
            stale_connections.append(connection)

    for connection in stale_connections:
        if connection in active_connections:
            active_connections.remove(connection)


async def run_and_broadcast(request: ExperimentRequest):
    await broadcast(
        {
            "type": "experiment_started",
            "experiment": request.name,
            "target": request.target,
            "dry_run": request.dry_run,
        }
    )
    result = orchestrator.run_experiment(
        request.name,
        request.target,
        request.duration_override,
        request.dry_run,
    )
    await broadcast({"type": "experiment_completed", "result": result})


@app.post("/api/experiments/run")
async def run_experiment(request: ExperimentRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_and_broadcast, request)
    return {
        "status": "accepted",
        "experiment": request.name,
        "target": request.target,
        "ws_endpoint": "/ws",
    }


@app.get("/api/experiments")
async def list_experiments():
    return [
        {
            "id": experiment_id,
            "name": experiment.name,
            "module": experiment.module,
            "target": experiment.target,
            "default_duration": experiment.default_duration or experiment.duration or 30,
            "dangerous": experiment.dangerous,
        }
        for experiment_id, experiment in orchestrator.config.experiments.items()
    ]


@app.get("/api/targets")
async def list_targets():
    return [
        {
            "id": target_id,
            "host": target.host,
            "user": target.user,
            "target_type": target.target_type,
        }
        for target_id, target in orchestrator.config.targets.items()
    ]

@app.get("/api/k8s/pods")
async def list_agent_pods():
    if not k8s_client:
        return {"error": "K8s client not configured or kubernetes package missing."}
    try:
        pods = k8s_client.discover_agent_pods()
        return {"pods": pods}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/platform/safety")
async def get_safety_policy():
    return orchestrator.config.safety.model_dump()


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


@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    template = ROOT_DIR / "frontend" / "templates" / "settings.html"
    return template.read_text(encoding="utf-8")


@app.get("/api/config")
async def get_config():
    return orchestrator.config.model_dump()


@app.post("/api/config/save")
async def save_config(config_data: dict):
    from backend.models import PlatformConfig
    from backend.config import ConfigError
    try:
        validated_config = PlatformConfig.model_validate(config_data)
        orchestrator.config = validated_config
        orchestrator.save_config()
        orchestrator.reload_config()
        return {"status": "ok", "message": "Configuration saved and applied successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/webhook/prometheus")
async def prometheus_webhook(alert: dict):
    return {"status": "received", "alert": alert}

