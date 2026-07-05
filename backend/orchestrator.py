from copy import deepcopy
from datetime import datetime
from importlib import import_module
import json
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
    "safety": {
        "dry_run": True,
        "allowed_targets": ["demo-node-1"],
        "default_target": "demo-node-1",
        "max_duration_seconds": 120,
        "allow_dangerous_actions": False,
        "auto_rollback": True,
        "audit_log_path": "chaos_audit.log",
    },
    "hypothesis": {
        "prometheus_url": "http://localhost:9090",
        "checks": [],
    },
    "experiments": {
        "cpu_stress": {"name": "CPU stress", "module": "cpu_stress", "default_duration": 30, "dangerous": True},
        "disk_fill": {"name": "Disk fill", "module": "disk_fill", "dangerous": True},
        "memory_stress": {"name": "Memory stress", "module": "memory_stress", "default_duration": 30, "dangerous": True},
        "network_latency": {"name": "Network latency", "module": "network_latency", "default_duration": 30, "dangerous": True},
        "packet_loss": {"name": "Packet loss", "module": "packet_loss", "default_duration": 30, "dangerous": True},
        "dns_chaos": {"name": "DNS chaos", "module": "dns_chaos", "dangerous": True},
        "process_kill": {"name": "Process kill", "module": "process_kill", "dangerous": True},
        "docker_kill": {"name": "Docker kill", "module": "docker_kill", "dangerous": True},
        "http_flood": {"name": "HTTP flood", "module": "http_flood", "dangerous": True},
        "iptables_block": {"name": "iptables block", "module": "iptables_block", "dangerous": True},
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
        dry_run: Optional[bool] = None,
    ) -> dict[str, Any]:
        experiment = self._get_experiment(name)
        started_at = datetime.utcnow().isoformat()
        safety = self._safety_config()
        effective_target = (target or experiment.get("target")) if experiment else target
        effective_target = effective_target or safety.get("default_target")

        if not experiment:
            result = {
                "status": "error",
                "experiment": name,
                "target": effective_target,
                "started_at": started_at,
                "message": "Experiment not found",
            }
            self.history.append(result)
            self._audit("experiment_rejected", result)
            return result

        duration = self._duration_for(experiment, duration_override)
        effective_dry_run = safety["dry_run"] if dry_run is None else dry_run
        safety_error = self._validate_safety(
            experiment=experiment,
            target=effective_target,
            duration=duration,
            dry_run=effective_dry_run,
        )
        if safety_error:
            result = {
                "status": "rejected",
                "experiment": name,
                "target": effective_target,
                "started_at": started_at,
                "reason": safety_error,
                "dry_run": effective_dry_run,
            }
            self.history.append(result)
            self._audit("experiment_rejected", result)
            self.notifier.send(f"Chaos rejected: {name} ({safety_error})", level="warning")
            return result

        if not self.hypothesis.validate():
            result = {
                "status": "aborted",
                "experiment": name,
                "target": effective_target,
                "started_at": started_at,
                "reason": "System unhealthy",
                "hypothesis_results": self.hypothesis.results,
                "dry_run": effective_dry_run,
            }
            self.history.append(result)
            self._audit("experiment_aborted", result)
            self.notifier.send(f"Chaos aborted: {name}", level="error")
            return result

        self.running = True
        if effective_dry_run:
            module_result = {
                "status": "dry_run",
                "module": experiment.get("module", name),
                "duration": duration,
                "message": "Safety dry-run enabled; no chaos was injected.",
            }
            rollback_result = {"status": "skipped", "reason": "dry_run"}
            status = "dry_run"
        else:
            try:
                module_result = self._execute_module(name, experiment, duration)
                status = "started"
            except Exception as exc:
                module_result = {
                    "status": "error",
                    "module": experiment.get("module", name),
                    "error": str(exc),
                }
                status = "failed"

            if safety["auto_rollback"]:
                rollback_result = self._rollback_module(name, experiment)
            else:
                rollback_result = {
                    "status": "skipped",
                    "reason": "auto_rollback_disabled",
                }

        result = {
            "status": status,
            "experiment": name,
            "target": effective_target,
            "started_at": started_at,
            "finished_at": datetime.utcnow().isoformat(),
            "dry_run": effective_dry_run,
            "duration": duration,
            "baseline": self.watcher.snapshot(),
            "module_result": module_result,
            "rollback_result": rollback_result,
            "hypothesis_results": self.hypothesis.results,
        }
        self.history.append(result)
        self._audit("experiment_completed", result)
        self.running = False
        self.notifier.send(f"Chaos experiment {status}: {name}")
        return result

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists() or yaml is None:
            return deepcopy(DEFAULT_CONFIG)
        with self.config_path.open(encoding="utf-8") as config_file:
            return yaml.safe_load(config_file) or deepcopy(DEFAULT_CONFIG)

    def _safety_config(self) -> dict[str, Any]:
        safety = deepcopy(DEFAULT_CONFIG["safety"])
        safety.update(self.config.get("safety", {}))
        return safety

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
        duration: int,
    ) -> dict[str, Any]:
        module_name = experiment.get("module", name)
        module = import_module(f"modules.{module_name}")
        self._audit(
            "chaos_injection",
            {
                "experiment": name,
                "module": module_name,
                "duration": duration,
                "dangerous": experiment.get("dangerous", False),
            },
        )

        if "default_duration" in experiment or "duration" in experiment:
            try:
                return module.run(duration=duration)
            except TypeError:
                return module.run()
        return module.run()

    def _rollback_module(self, name: str, experiment: dict[str, Any]) -> dict[str, Any]:
        module_name = experiment.get("module", name)
        module = import_module(f"modules.{module_name}")
        rollback = getattr(module, "rollback", None)
        if rollback is None:
            result = {"status": "missing", "module": module_name}
        else:
            try:
                result = rollback()
            except Exception as exc:
                result = {
                    "status": "error",
                    "module": module_name,
                    "error": str(exc),
                }
        self._audit("chaos_rollback", {"experiment": name, "module": module_name, "result": result})
        return result

    def _duration_for(
        self,
        experiment: dict[str, Any],
        duration_override: Optional[int],
    ) -> int:
        return int(duration_override or experiment.get("duration") or experiment.get("default_duration", 30))

    def _validate_safety(
        self,
        experiment: dict[str, Any],
        target: Optional[str],
        duration: int,
        dry_run: bool,
    ) -> Optional[str]:
        safety = self._safety_config()
        allowed_targets = set(safety.get("allowed_targets", []))

        if not target:
            return "Target is required by safety policy."
        if allowed_targets and target not in allowed_targets:
            return f"Target '{target}' is not in the allowlist."
        if duration > int(safety.get("max_duration_seconds", 120)):
            return f"Duration {duration}s exceeds max_duration_seconds."
        if experiment.get("dangerous", False) and not dry_run and not safety.get("allow_dangerous_actions", False):
            return "Dangerous chaos actions require safety.allow_dangerous_actions=true."
        return None

    def _audit(self, event: str, payload: dict[str, Any]):
        record = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }
        log_path = Path(self._safety_config().get("audit_log_path", "chaos_audit.log"))
        if not log_path.is_absolute():
            log_path = self.config_path.parent.parent / log_path
        try:
            with log_path.open("a", encoding="utf-8") as audit_log:
                audit_log.write(json.dumps(record, ensure_ascii=True) + "\n")
        except OSError:
            pass
