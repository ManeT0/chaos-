from fastapi import FastAPI, WebSocket, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json

import hypothesis

app = FastAPI(title="Chaos Platform API", version="2.0")

# WebSocket connections
active_connections: List[WebSocket] = []

class ExperimentRequest(BaseModel):
    name: str
    target: str
    duration_override: Optional[int] = None

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        active_connections.remove(websocket)

async def broadcast(event: dict):
    """Отправляет событие всем подключенным WebSocket клиентам"""
    for connection in active_connections:
        try:
            await connection.send_json(event)
        except:
            active_connections.remove(connection)

@app.post("/api/experiments/run")
async def run_experiment(request: ExperimentRequest, background_tasks: BackgroundTasks):
    """Запуск эксперимента через API"""
    
    # В реальном коде здесь вызов orchestrator
    background_tasks.add_task(
        orchestrator.run_experiment, 
        request.name, 
        request.target
    )
    
    return {
        "status": "accepted",
        "experiment": request.name,
        "target": request.target,
        "ws_endpoint": "/ws"  # Для real-time обновлений
    }

@app.get("/api/experiments/history")
async def get_history(limit: int = 20):
    """History of all experiments"""
    return orchestrator.history[-limit:]

@app.get("/api/hypothesis/status")
async def get_system_health():
    """Current state of the system"""
    hypothesis.validate()
    return {
        "healthy": all(r["passed"] for r in hypothesis.results),
        "checks": hypothesis.results
    }

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Web UI dashboard"""
    with open("frontend/templates/dashboard.html") as f:
        return f.read()

# endpoint for Prometheus AlertManager
@app.post("/api/webhook/prometheus")
async def prometheus_webhook(alert: dict):
    """getting alerts from AlertManager and can trigger chaos"""
    # ex: if CPU low — run test automatically
    pass