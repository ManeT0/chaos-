from datetime import datetime
import json
from pathlib import Path
from typing import Any, Optional

from backend.config import load_platform_config
from backend.hypothesis import HypothesisCheck, SteadyStateHypothesis
from backend.models import ExperimentConfig, PlatformConfig, SafetyConfig
from backend.notifier import Notifier
from backend.prometheus_watcher import PrometheusWatcher
from modules.registry import get_module


class Orchestrator:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path or Path(__file__).with_name("config.yaml"))
        self.config = self._load_config()
        self.running = False
        self.active_experiments: dict[str, dict[str, Any]] = {}
        self.history: list[dict[str, Any]] = []

        hypothesis_config = self.config.hypothesis
        self.hypothesis = SteadyStateHypothesis(
            hypothesis_config.prometheus_url
        )
        for check in hypothesis_config.checks:
            self.hypothesis.add_check(HypothesisCheck(**check.model_dump()))

        self.watcher = PrometheusWatcher(self.hypothesis.prometheus_url)
        self.notifier = Notifier(self.config.notifications.model_dump())

    def save_config(self):
        from backend.config import save_platform_config
        save_platform_config(self.config, self.config_path)

    def reload_config(self):
        self.config = self._load_config()
        # Re-initialize modules/dependencies if they changed
        hypothesis_config = self.config.hypothesis
        self.hypothesis = SteadyStateHypothesis(
            hypothesis_config.prometheus_url
        )
        for check in hypothesis_config.checks:
            self.hypothesis.add_check(HypothesisCheck(**check.model_dump()))
        self.watcher = PrometheusWatcher(self.hypothesis.prometheus_url)
        self.notifier = Notifier(self.config.notifications.model_dump())


    def run_experiment(
        self,
        name: str,
        target: Optional[str] = None,
        duration_override: Optional[int] = None,
        dry_run: Optional[bool] = None,
    ) -> dict[str, Any]:
        experiment = self._get_experiment(name)
        started_at = datetime.utcnow().isoformat()
        safety = self.config.safety
        effective_target = (target or experiment.target) if experiment else target
        effective_target = effective_target or safety.default_target

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
        effective_dry_run = safety.dry_run if dry_run is None else dry_run
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
                "module": experiment.module,
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
                    "module": experiment.module,
                    "error": str(exc),
                }
                status = "failed"

            if safety.auto_rollback:
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

    def _load_config(self) -> PlatformConfig:
        return load_platform_config(self.config_path)

    def _safety_config(self) -> SafetyConfig:
        return self.config.safety

    def _get_experiment(self, name: str) -> Optional[ExperimentConfig]:
        return self.config.experiments.get(name)

    def _execute_module(
        self,
        name: str,
        experiment: ExperimentConfig,
        duration: int,
    ) -> dict[str, Any]:
        module_name = experiment.module
        module = get_module(module_name)
        if module is None:
            raise ValueError(f"Chaos module '{module_name}' is not registered.")

        self._audit(
            "chaos_injection",
            {
                "experiment": name,
                "module": module_name,
                "duration": duration,
                "dangerous": experiment.dangerous,
            },
        )

        if experiment.default_duration is not None or experiment.duration is not None:
            try:
                return module.run(duration=duration)
            except TypeError:
                return module.run()
        return module.run()

    def _rollback_module(self, name: str, experiment: ExperimentConfig) -> dict[str, Any]:
        module_name = experiment.module
        module = get_module(module_name)
        if module is None:
            result = {"status": "missing", "module": module_name}
        elif module.rollback is None:
            result = {"status": "missing", "module": module_name}
        else:
            try:
                result = module.rollback()
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
        experiment: ExperimentConfig,
        duration_override: Optional[int],
    ) -> int:
        return int(duration_override or experiment.duration or experiment.default_duration or 30)

    def _validate_safety(
        self,
        experiment: ExperimentConfig,
        target: Optional[str],
        duration: int,
        dry_run: bool,
    ) -> Optional[str]:
        safety = self.config.safety
        allowed_targets = set(safety.allowed_targets)

        if not target:
            return "Target is required by safety policy."
        if allowed_targets and target not in allowed_targets:
            return f"Target '{target}' is not in the allowlist."
        if duration > safety.max_duration_seconds:
            return f"Duration {duration}s exceeds max_duration_seconds."
        if experiment.dangerous and not dry_run and not safety.allow_dangerous_actions:
            return "Dangerous chaos actions require safety.allow_dangerous_actions=true."
        if get_module(experiment.module) is None:
            return f"Chaos module '{experiment.module}' is not registered."
        return None

    def _audit(self, event: str, payload: dict[str, Any]):
        record = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }
        log_path = Path(self.config.safety.audit_log_path)
        if not log_path.is_absolute():
            log_path = self.config_path.parent.parent / log_path
        try:
            with log_path.open("a", encoding="utf-8") as audit_log:
                audit_log.write(json.dumps(record, ensure_ascii=True) + "\n")
        except OSError:
            pass
