from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


@dataclass
class HypothesisCheck:
    name: str
    promql: str
    operator: str
    threshold: float
    description: str = ""


class SteadyStateHypothesis:
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url.rstrip("/")
        self.checks: List[HypothesisCheck] = []
        self.results: List[Dict[str, Any]] = []

    def add_check(self, check: HypothesisCheck):
        self.checks.append(check)

    def query_prometheus(self, promql: str) -> Optional[float]:
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": promql},
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            result = data.get("data", {}).get("result", [])
            if data.get("status") == "success" and result:
                return float(result[0]["value"][1])
        except Exception:
            return None
        return None

    def validate(self) -> bool:
        self.results = []
        all_passed = True

        for check in self.checks:
            value = self.query_prometheus(check.promql)
            if value is None:
                self.results.append(
                    {
                        "check": check.name,
                        "passed": False,
                        "error": "No data from Prometheus",
                    }
                )
                all_passed = False
                continue

            passed = self._compare(value, check.operator, check.threshold)
            self.results.append(
                {
                    "check": check.name,
                    "passed": passed,
                    "value": value,
                    "threshold": check.threshold,
                    "description": check.description,
                }
            )
            all_passed = all_passed and passed

        return all_passed

    @staticmethod
    def _compare(value: float, operator: str, threshold: float) -> bool:
        if operator == "lt":
            return value < threshold
        if operator == "lte":
            return value <= threshold
        if operator == "gt":
            return value > threshold
        if operator == "gte":
            return value >= threshold
        if operator == "eq":
            return value == threshold
        return False


class HypothesisValidator:
    def evaluate(self, checks: list[dict[str, Any]]) -> bool:
        return all(
            check.get("value", 0) >= check.get("threshold", 0)
            for check in checks
        )
