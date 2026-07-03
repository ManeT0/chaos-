import requests
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class HypothesisCheck:
    name: str
    promql: str           # Prometheus Query
    operator: str          # "lt", "gt", "eq"
    threshold: float
    description: str

class SteadyStateHypothesis:
    """Checks that the system is in a steady state before chaos"""
    
    def __init__(self, prometheus_url: str):
        self.prometheus_url = prometheus_url
        self.checks: List[HypothesisCheck] = []
        self.results: List[Dict] = []
    
    def add_check(self, check: HypothesisCheck):
        self.checks.append(check)
    
    def query_prometheus(self, promql: str) -> Optional[float]:
        """Запрос к Prometheus API"""
        try:
            resp = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": promql},
                timeout=5
            )
            data = resp.json()
            if data["status"] == "success" and data["data"]["result"]:
                return float(data["data"]["result"][0]["value"][1])
        except Exception as e:
            print(f"Prometheus query failed: {e}")
        return None
    
    def validate(self) -> bool:
        """Returns True if the system is healthy"""
        self.results = []
        all_passed = True
        
        for check in self.checks:
            value = self.query_prometheus(check.promql)
            
            if value is None:
                self.results.append({
                    "check": check.name,
                    "passed": False,
                    "error": "No data from Prometheus"
                })
                all_passed = False
                continue
            
            if check.operator == "lt":
                passed = value < check.threshold
            elif check.operator == "gt":
                passed = value > check.threshold
            elif check.operator == "eq":
                passed = value == check.threshold
            else:
                passed = False
            
            self.results.append({
                "check": check.name,
                "passed": passed,
                "value": value,
                "threshold": check.threshold,
                "description": check.description
            })
            
            if not passed:
                all_passed = False
        
        return all_passed