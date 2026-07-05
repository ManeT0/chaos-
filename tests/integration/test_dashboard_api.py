from fastapi.testclient import TestClient

from backend.main import app, orchestrator


client = TestClient(app)


def test_dashboard_experiments_endpoint_lists_configured_experiments():
    response = client.get("/api/experiments")

    assert response.status_code == 200
    experiments = response.json()
    assert any(experiment["id"] == "cpu_stress" for experiment in experiments)


def test_dashboard_targets_endpoint_lists_configured_targets():
    response = client.get("/api/targets")

    assert response.status_code == 200
    targets = response.json()
    assert any(target["id"] == "demo-node-1" for target in targets)


def test_dashboard_run_endpoint_updates_history():
    orchestrator.history.clear()

    response = client.post(
        "/api/experiments/run",
        json={
            "name": "cpu_stress",
            "target": "demo-node-1",
            "dry_run": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert orchestrator.history[-1]["status"] == "dry_run"


def test_dashboard_page_serves_app_shell():
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Run Experiment" in response.text
