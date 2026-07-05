from backend.orchestrator import Orchestrator


def test_run_experiment_uses_dry_run_by_default():
    orchestrator = Orchestrator()
    result = orchestrator.run_experiment("cpu_stress")
    assert result["status"] == "dry_run"
    assert result["module_result"]["status"] == "dry_run"


def test_rejects_target_outside_allowlist():
    orchestrator = Orchestrator()
    result = orchestrator.run_experiment("cpu_stress", target="prod-node-1")
    assert result["status"] == "rejected"
    assert "allowlist" in result["reason"]


def test_rejects_duration_above_safety_limit():
    orchestrator = Orchestrator()
    result = orchestrator.run_experiment("cpu_stress", duration_override=999)
    assert result["status"] == "rejected"
    assert "max_duration_seconds" in result["reason"]


def test_rejects_dangerous_real_run_without_explicit_config():
    orchestrator = Orchestrator()
    result = orchestrator.run_experiment("cpu_stress", dry_run=False)
    assert result["status"] == "rejected"
    assert "allow_dangerous_actions" in result["reason"]


def test_real_run_rolls_back_when_explicitly_allowed():
    orchestrator = Orchestrator()
    orchestrator.config.safety.allow_dangerous_actions = True

    result = orchestrator.run_experiment("cpu_stress", dry_run=False)

    assert result["status"] == "started"
    assert result["module_result"]["status"] == "ok"
    assert result["rollback_result"]["status"] == "rolled_back"
