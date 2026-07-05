from datetime import datetime
from copy import deepcopy
from importlib import import_module
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

from backend.hypothesis import HypothesisCheck, SteadyStateHypothesis
from backend.notifier import Notifier
from backend.prometheus_watcher import PrometheusWatcher


DEFAULT_CONFIG = {
    "hypothesis": {
        "prometheus_url": "http://localhost:9090",
        "checks": [],
    },
    "experiments": {
        "cpu_stress": {"name": "CPU stress", "module": "cpu_stress", "default_duration": 30},
        "disk_fill": {"name": "Disk fill", "module": "disk_fill"},
        "memory_stress": {"name": "Memory stress", "module": "memory_stress", "default_duration": 30},
        "network_latency": {"name": "Network latency", "module": "network_latency", "default_duration": 30},
        "packet_loss": {"name": "Packet loss", "module": "packet_loss", "default_duration": 30},
        "dns_chaos": {"name": "DNS chaos", "module": "dns_chaos"},
        "process_kill": {"name": "Process kill", "module": "process_kill"},
        "docker_kill": {"name": "Docker kill", "module": "docker_kill"},
        "http_flood": {"name": "HTTP flood", "module": "http_flood"},
        "iptables_block": {"name": "iptables block", "module": "iptables_block"},
    },
    "notifications": {},
}


class Orchestrator:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path or Path(__file__).with_name("config.yaml"))
        self.config = self._load_config()
        self.running = False
        self.active_experiments: dict[str, dict[str, Any]] = {}
        self.history: list[dict[str, Any]] = []

        hypothesis_config = self.config.get("hypothesis", {})
        self.hypothesis = SteadyStateHypothesis(
            hypothesis_config.get("prometheus_url", "http://localhost:9090")
        )
        for check in hypothesis_config.get("checks", []):
            self.hypothesis.add_check(HypothesisCheck(**check))

        self.watcher = PrometheusWatcher(self.hypothesis.prometheus_url)
        self.notifier = Notifier(self.config.get("notifications", {}))

    def run_experiment(
        self,
        name: str,
        target: Optional[str] = None,
        duration_override: Optional[int] = None,
    ) -> dict[str, Any]:
        experiment = self._get_experiment(name)
        started_at = datetime.utcnow().isoformat()

        if not experiment:
            result = {
                "status": "error",
                "experiment": name,
                "target": target,
                "started_at": started_at,
                "message": "Experiment not found",
            }
            self.history.append(result)
            return result

        if not self.hypothesis.validate():
            result = {
                "status": "aborted",
                "experiment": name,
                "target": target,
                "started_at": started_at,
                "reason": "System unhealthy",
                "hypothesis_results": self.hypothesis.results,
            }
            self.history.append(result)
            self.notifier.send(f"Chaos aborted: {name}", level="error")
            return result

        self.running = True
        module_result = self._execute_module(name, experiment, duration_override)
        result = {
            "status": "started",
            "experiment": name,
            "target": target,
            "started_at": started_at,
            "finished_at": datetime.utcnow().isoformat(),
            "baseline": self.watcher.snapshot(),
            "module_result": module_result,
            "hypothesis_results": self.hypothesis.results,
        }
        self.history.append(result)
        self.notifier.send(f"Chaos experiment started: {name}")
        return result

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists() or yaml is None:
            return deepcopy(DEFAULT_CONFIG)
        with self.config_path.open(encoding="utf-8") as config_file:
            return yaml.safe_load(config_file) or deepcopy(DEFAULT_CONFIG)

    def _get_experiment(self, name: str) -> Optional[dict[str, Any]]:
        experiments = self.config.get("experiments", {})
        if isinstance(experiments, dict):
            return experiments.get(name)
        for experiment in experiments:
            if experiment.get("name") == name:
                return experiment
        return None

    def _execute_module(
        self,
        name: str,
        experiment: dict[str, Any],
        duration_override: Optional[int],
    ) -> dict[str, Any]:
        module_name = experiment.get("module", name)
        duration = duration_override or experiment.get("default_duration", 30)
        module = import_module(f"modules.{module_name}")

        if "default_duration" in experiment or "duration" in experiment:
            try:
                return module.run(duration=duration)
            except TypeError:
                return module.run()
        return module.run()
