import pytest

from backend.config import ConfigError, _validate_config_relations
from backend.models import PlatformConfig


def test_platform_config_validates_known_shape():
    config = PlatformConfig.model_validate(
        {
            "targets": {
                "demo-node-1": {
                    "host": "localhost",
                    "user": "root",
                },
            },
            "experiments": {
                "cpu_stress": {
                    "name": "CPU stress",
                    "module": "cpu_stress",
                    "default_duration": 30,
                },
            },
        }
    )

    assert config.experiments["cpu_stress"].module == "cpu_stress"


def test_platform_config_rejects_unknown_fields():
    with pytest.raises(ValueError):
        PlatformConfig.model_validate({"unexpected": True})


def test_config_relations_reject_unregistered_module():
    config = PlatformConfig.model_validate(
        {
            "targets": {
                "demo-node-1": {
                    "host": "localhost",
                    "user": "root",
                },
            },
            "experiments": {
                "bad": {
                    "name": "Bad experiment",
                    "module": "not_registered",
                },
            },
        }
    )

    with pytest.raises(ConfigError):
        _validate_config_relations(config)


def test_config_relations_reject_schedule_unknown_experiment():
    config = PlatformConfig.model_validate(
        {
            "targets": {
                "demo-node-1": {
                    "host": "localhost",
                    "user": "root",
                },
            },
            "schedules": [
                {
                    "name": "bad-schedule",
                    "cron": "0 9 * * 1",
                    "experiment": "missing",
                },
            ],
        }
    )

    with pytest.raises(ConfigError):
        _validate_config_relations(config)
