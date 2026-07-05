from modules.cpu_stress import run as cpu_run


def test_cpu_module_runs():
    result = cpu_run(10)
    assert result["status"] == "ok"
