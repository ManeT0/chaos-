from pathlib import Path
from typing import List, Annotated
import datetime

from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from backend.models import ExperimentRequest, UserConfig
from backend.orchestrator import Orchestrator
from backend.auth import (
    set_users, verify_password, create_access_token, get_current_user, require_role, ACCESS_TOKEN_EXPIRE_MINUTES
)

try:
    from backend.k8s_agent_client import ChaosAgentClient
    k8s_client = ChaosAgentClient()
except ImportError:
    k8s_client = None

ROOT_DIR = Path(__file__).resolve().parents[1]

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Chaos Platform API", version="2.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

FastAPIInstrumentor.instrument_app(app)

app.mount(
    "/static",
    StaticFiles(directory=ROOT_DIR / "frontend" / "static"),
    name="static",
)

orchestrator = Orchestrator()
# Initialize auth users
set_users(orchestrator.config.safety.users)

active_connections: List[WebSocket] = []

@app.post("/api/auth/token")
@limiter.limit("5/minute")
async def login_for_access_token(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    users = orchestrator.config.safety.users
    user = next((u for u in users if u.username == form_data.username), None)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
async def read_users_me(current_user: UserConfig = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}

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
@limiter.limit("10/minute")
async def run_experiment(
    request: Request,
    exp_request: ExperimentRequest, 
    background_tasks: BackgroundTasks,
    current_user: UserConfig = Depends(require_role(["admin", "operator"]))
):
    target_config = orchestrator.config.targets.get(exp_request.target)
    if not target_config:
        raise HTTPException(status_code=404, detail="Target not found")
        
    if target_config.labels.get("env") == "prod" and orchestrator.config.safety.require_prod_confirmation:
        if not exp_request.confirm_prod:
            raise HTTPException(
                status_code=400, 
                detail="Production target selected. Explicit confirmation is required (confirm_prod=True)."
            )
            
    background_tasks.add_task(run_and_broadcast, exp_request)
    return {
        "status": "accepted",
        "experiment": exp_request.name,
        "target": exp_request.target,
        "ws_endpoint": "/ws",
    }

@app.get("/api/experiments")
async def list_experiments(current_user: UserConfig = Depends(get_current_user)):
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
async def list_targets(current_user: UserConfig = Depends(get_current_user)):
    return [
        {
            "id": target_id,
            "host": target.host,
            "user": target.user,
            "target_type": target.target_type,
            "labels": target.labels,
        }
        for target_id, target in orchestrator.config.targets.items()
    ]

@app.get("/api/k8s/pods")
async def list_agent_pods(current_user: UserConfig = Depends(require_role(["admin", "operator"]))):
    if not k8s_client:
        return {"error": "K8s client not configured or kubernetes package missing."}
    try:
        pods = k8s_client.discover_agent_pods()
        return {"pods": pods}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/platform/safety")
async def get_safety_policy(current_user: UserConfig = Depends(get_current_user)):
    return orchestrator.config.safety.model_dump(exclude={"users"})

@app.get("/api/experiments/history")
async def get_history(limit: int = 20, current_user: UserConfig = Depends(get_current_user)):
    return orchestrator.history[-limit:]

@app.get("/api/hypothesis/status")
async def get_system_health(current_user: UserConfig = Depends(get_current_user)):
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
async def get_config(current_user: UserConfig = Depends(require_role(["admin", "operator"]))):
    return orchestrator.config.model_dump()

@app.post("/api/config/save")
async def save_config(config_data: dict, current_user: UserConfig = Depends(require_role(["admin"]))):
    from backend.models import PlatformConfig
    from backend.config import ConfigError
    try:
        validated_config = PlatformConfig.model_validate(config_data)
        orchestrator.config = validated_config
        orchestrator.save_config()
        orchestrator.reload_config()
        set_users(orchestrator.config.safety.users) # Reload users
        return {"status": "ok", "message": "Configuration saved and applied successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/webhook/prometheus")
async def prometheus_webhook(alert: dict):
    return {"status": "received", "alert": alert}

