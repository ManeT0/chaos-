from typing import Optional

import requests


class PrometheusWatcher:
    def __init__(self, base_url: str = "http://localhost:9090"):
        self.base_url = base_url.rstrip("/")

    def query(self, promql: str) -> Optional[float]:
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/query",
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

    def snapshot(self) -> dict[str, Optional[float]]:
        return {
            "error_rate": self.get_error_rate(),
            "p99_latency_ms": self.get_p99_latency(),
        }

    def get_error_rate(self) -> float:
        value = self.query(
            "rate(http_requests_total{status=~'5..'}[5m]) / "
            "rate(http_requests_total[5m])"
        )
        return value or 0.0

    def get_p99_latency(self) -> float:
        value = self.query(
            "histogram_quantile(0.99, "
            "rate(http_request_duration_seconds_bucket[5m]))"
        )
        return (value or 0.0) * 1000
