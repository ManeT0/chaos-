from typing import Any, Optional

from pydantic import BaseModel, Field


class ExperimentRequest(BaseModel):
    name: str = Field(..., examples=["cpu_stress"])
    target: Optional[str] = Field(default=None, examples=["demo-node-1"])
    duration_override: Optional[int] = Field(default=None, ge=1)
    dry_run: Optional[bool] = Field(
        default=None,
        description="Override the platform dry-run mode for this request.",
    )


class ExperimentResult(BaseModel):
    status: str
    experiment: str
    target: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None
    module_result: dict[str, Any] = Field(default_factory=dict)
    hypothesis_results: list[dict[str, Any]] = Field(default_factory=list)
