from backend.orchestrator import Orchestrator


def test_run_experiment_starts_experiment():
    orchestrator = Orchestrator()
    result = orchestrator.run_experiment("cpu_stress")
    assert result["status"] == "started"
