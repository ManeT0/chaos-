from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.models import PlatformConfig
from modules.registry import get_module

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


DEFAULT_CONFIG_DATA: dict[str, Any] = {
    "targets": {
        "demo-node-1": {
            "host": "localhost",
            "user": "root",
        },
    },
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
        "cpu_stress": {
            "name": "CPU stress",
            "module": "cpu_stress",
            "default_duration": 30,
            "dangerous": True,
        },
        "disk_fill": {
            "name": "Disk fill",
            "module": "disk_fill",
            "dangerous": True,
        },
        "memory_stress": {
            "name": "Memory stress",
            "module": "memory_stress",
            "default_duration": 30,
            "dangerous": True,
        },
        "network_latency": {
            "name": "Network latency",
            "module": "network_latency",
            "default_duration": 30,
            "dangerous": True,
        },
        "packet_loss": {
            "name": "Packet loss",
            "module": "packet_loss",
            "default_duration": 30,
            "dangerous": True,
        },
        "dns_chaos": {
            "name": "DNS chaos",
            "module": "dns_chaos",
            "dangerous": True,
        },
        "process_kill": {
            "name": "Process kill",
            "module": "process_kill",
            "dangerous": True,
        },
        "docker_kill": {
            "name": "Docker kill",
            "module": "docker_kill",
            "dangerous": True,
        },
        "http_flood": {
            "name": "HTTP flood",
            "module": "http_flood",
            "dangerous": True,
        },
        "iptables_block": {
            "name": "iptables block",
            "module": "iptables_block",
            "dangerous": True,
        },
    },
    "schedules": [],
    "notifications": {},
}


class ConfigError(ValueError):
    pass


def load_platform_config(config_path: str | Path) -> PlatformConfig:
    path = Path(config_path)
    if not path.exists() or yaml is None:
        config = PlatformConfig.model_validate(deepcopy(DEFAULT_CONFIG_DATA))
        _validate_config_relations(config)
        return config

    with path.open(encoding="utf-8") as config_file:
        raw_config = yaml.safe_load(config_file) or {}

    from backend.secrets import resolve_secrets
    raw_config = resolve_secrets(raw_config)

    try:
        config = PlatformConfig.model_validate(raw_config)
    except ValidationError as exc:
        raise ConfigError(f"Invalid platform config: {exc}") from exc

    _validate_config_relations(config)
    return config


def _validate_config_relations(config: PlatformConfig):
    target_names = set(config.targets)

    if config.safety.default_target and config.safety.default_target not in target_names:
        raise ConfigError(
            f"Invalid platform config: safety.default_target "
            f"'{config.safety.default_target}' is not defined in targets."
        )

    unknown_allowed_targets = set(config.safety.allowed_targets) - target_names
    if unknown_allowed_targets:
        targets = ", ".join(sorted(unknown_allowed_targets))
        raise ConfigError(
            f"Invalid platform config: safety.allowed_targets contains unknown targets: {targets}."
        )

    for experiment_name, experiment in config.experiments.items():
        if get_module(experiment.module) is None:
            raise ConfigError(
                f"Invalid platform config: experiment '{experiment_name}' references "
                f"unregistered chaos module '{experiment.module}'."
            )
        if experiment.target and experiment.target not in target_names:
            raise ConfigError(
                f"Invalid platform config: experiment '{experiment_name}' references "
                f"unknown target '{experiment.target}'."
            )

    for schedule in config.schedules:
        if schedule.experiment not in config.experiments:
            raise ConfigError(
                f"Invalid platform config: schedule '{schedule.name}' references "
                f"unknown experiment '{schedule.experiment}'."
            )
        if schedule.target and schedule.target not in target_names:
            raise ConfigError(
                f"Invalid platform config: schedule '{schedule.name}' references "
                f"unknown target '{schedule.target}'."
            )


def save_platform_config(config: PlatformConfig, config_path: str | Path) -> None:
    if yaml is None:
        raise ConfigError("PyYAML is not installed; cannot save configuration.")
    path = Path(config_path)
    
    # Serialize config using Pydantic, dump to dict, clean None fields if necessary
    data = config.model_dump(exclude_none=True)
    
    with path.open("w", encoding="utf-8") as config_file:
        yaml.safe_dump(data, config_file, default_flow_style=False, allow_unicode=True)

