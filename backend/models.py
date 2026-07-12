from typing import Any, Literal, Optional, List, Dict

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExperimentRequest(StrictModel):
    name: str = Field(..., examples=["cpu_stress"])
    target: Optional[str] = Field(default=None, examples=["demo-node-1"])
    duration_override: Optional[int] = Field(default=None, ge=1)
    dry_run: Optional[bool] = Field(
        default=None,
        description="Override the platform dry-run mode for this request.",
    )
    confirm_prod: Optional[bool] = Field(
        default=False,
        description="Must be set to true if running on a target labeled with env=prod."
    )


class ExperimentResult(StrictModel):
    status: str
    experiment: str
    target: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None
    module_result: dict[str, Any] = Field(default_factory=dict)
    hypothesis_results: list[dict[str, Any]] = Field(default_factory=list)


class KubernetesTargetConfig(StrictModel):
    namespace: str = "default"
    pod_selector: Dict[str, str] = Field(default_factory=dict)
    target_type: Literal["grpc-agent", "chaos-mesh", "litmus"] = "grpc-agent"
    grpc_port: int = 50051

class TargetConfig(StrictModel):
    host: str
    user: str
    key_path: Optional[str] = None
    target_type: Literal["ssh", "kubernetes", "agent"] = "ssh"
    kubernetes: Optional[KubernetesTargetConfig] = None
    labels: Dict[str, str] = Field(default_factory=dict)
    agent_url: Optional[str] = None
    agent_token: Optional[str] = None

class UserConfig(StrictModel):
    username: str
    password_hash: str
    role: Literal["admin", "operator", "viewer"] = "viewer"

class TeamConfig(StrictModel):
    id: str
    name: str
    members: List[str] = Field(default_factory=list)
    allowed_targets: List[str] = Field(default_factory=list)
    allowed_experiments: List[str] = Field(default_factory=list)

class ProjectConfig(StrictModel):
    id: str
    name: str
    team_id: str
    slo_target: float = 99.9
    error_budget_minutes: int = 43

class SLOConfig(StrictModel):
    name: str
    prometheus_expr: str
    target_ratio: float
    window_hours: int = 720

class SafetyConfig(StrictModel):
    dry_run: bool = True
    allowed_targets: List[str] = Field(default_factory=list)
    default_target: Optional[str] = None
    max_duration_seconds: int = Field(default=120, ge=1)
    allow_dangerous_actions: bool = False
    auto_rollback: bool = True
    audit_log_path: str = "chaos_audit.log"
    users: List[UserConfig] = Field(default_factory=list)
    allowed_environments: List[str] = Field(default_factory=list)
    max_concurrent_targets: int = 1
    require_prod_confirmation: bool = True

ProbeType = Literal["prometheus", "datadog", "newrelic", "elastic", "http", "tcp", "script"]

class HypothesisCheckConfig(StrictModel):
    name: str
    probe_type: ProbeType = "prometheus"
    promql: Optional[str] = None
    operator: Optional[Literal["lt", "lte", "gt", "gte", "eq"]] = None
    threshold: Optional[float] = None
    description: str = ""
    url: Optional[str] = None
    expected_status: Optional[int] = None
    body_regex: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    script_path: Optional[str] = None
    timeout_seconds: Optional[int] = 5
    datadog_query: Optional[str] = None
    newrelic_nrql: Optional[str] = None
    elastic_index: Optional[str] = None
    elastic_query: Optional[str] = None


class CheckGroupConfig(StrictModel):
    name: str
    mode: Literal["AND", "OR"] = "AND"
    checks: List[HypothesisCheckConfig] = Field(default_factory=list)

class HypothesisConfig(StrictModel):
    prometheus_url: str = "http://localhost:9090"
    mode: Literal["AND", "OR"] = "AND"
    check_groups: List[CheckGroupConfig] = Field(default_factory=list)
    checks: List[HypothesisCheckConfig] = Field(default_factory=list)

class ExperimentConfig(StrictModel):
    name: str
    module: str
    default_duration: Optional[int] = Field(default=None, ge=1)
    duration: Optional[int] = Field(default=None, ge=1)
    dangerous: bool = False
    target: Optional[str] = None

class ExperimentTemplateConfig(StrictModel):
    name: str
    description: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    experiment: ExperimentConfig

class ScheduleConfig(StrictModel):
    name: str
    cron: str
    experiment: str
    target: Optional[str] = None


class TelegramConfig(StrictModel):
    token: str = ""
    chat_id: str = ""


class SlackConfig(StrictModel):
    webhook: str = ""


class NotificationsConfig(StrictModel):
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    teams_webhook: str = ""
    pagerduty_routing_key: str = ""


class PlatformConfig(StrictModel):
    targets: dict[str, TargetConfig] = Field(default_factory=dict)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    hypothesis: HypothesisConfig = Field(default_factory=HypothesisConfig)
    experiments: dict[str, ExperimentConfig] = Field(default_factory=dict)
    schedules: list[ScheduleConfig] = Field(default_factory=list)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    teams: list[TeamConfig] = Field(default_factory=list)
    projects: list[ProjectConfig] = Field(default_factory=list)
    slos: list[SLOConfig] = Field(default_factory=list)
