import asyncio
import time
import socket
import re
import subprocess
from typing import Any, Dict, List, Optional
import requests
import httpx

from .models import HypothesisConfig, CheckGroupConfig, HypothesisCheckConfig


class SteadyStateHypothesis:
    def __init__(self, config: HypothesisConfig):
        self.config = config
        self.prometheus_url = config.prometheus_url.rstrip("/")
        self.results: List[Dict[str, Any]] = []

    async def execute(self) -> bool:
        self.results = []
        all_passed = True
        
        # Legacy checks at top level
        if self.config.checks:
            group_passed = await self._execute_group(self.config.checks, mode="AND")
            all_passed = all_passed and group_passed

        # Groups
        group_results = []
        for group in self.config.check_groups:
            group_passed = await self._execute_group(group.checks, mode=group.mode)
            group_results.append(group_passed)
        
        if self.config.check_groups:
            if self.config.mode == "AND":
                all_passed = all_passed and all(group_results)
            elif self.config.mode == "OR":
                all_passed = all_passed and any(group_results)

        return all_passed

    async def _execute_group(self, checks: List[HypothesisCheckConfig], mode: str) -> bool:
        if not checks:
            return True
            
        tasks = [self._execute_check(check) for check in checks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        group_passed = True if mode == "AND" else False
        for res in results:
            if isinstance(res, Exception):
                self.results.append({"error": str(res), "passed": False})
                if mode == "AND":
                    group_passed = False
                continue
            
            self.results.append(res)
            passed = res.get("passed", False)
            
            if mode == "AND":
                group_passed = group_passed and passed
            elif mode == "OR":
                group_passed = group_passed or passed
                
        return group_passed

    async def _execute_check(self, check: HypothesisCheckConfig) -> Dict[str, Any]:
        start_time = time.time()
        result = {
            "check": check.name,
            "probe_type": check.probe_type,
            "description": check.description,
            "passed": False,
            "value": None,
            "threshold": check.threshold,
            "latency_ms": 0,
            "error": None
        }

        try:
            if check.probe_type == "prometheus":
                await self._probe_prometheus(check, result)
            elif check.probe_type == "http":
                await self._probe_http(check, result)
            elif check.probe_type == "tcp":
                await self._probe_tcp(check, result)
            elif check.probe_type == "script":
                await self._probe_script(check, result)
            elif check.probe_type in ["datadog", "newrelic", "elastic"]:
                result["error"] = f"{check.probe_type} probe not fully implemented yet"
            else:
                result["error"] = f"Unsupported probe type: {check.probe_type}"
        except Exception as e:
            result["error"] = str(e)
            
        result["latency_ms"] = int((time.time() - start_time) * 1000)
        return result

    async def _probe_prometheus(self, check: HypothesisCheckConfig, result: Dict[str, Any]):
        if not check.promql:
            result["error"] = "promql missing"
            return
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": check.promql},
                timeout=check.timeout_seconds
            )
            resp.raise_for_status()
            data = resp.json()
            res_data = data.get("data", {}).get("result", [])
            if res_data:
                val = float(res_data[0]["value"][1])
                result["value"] = val
                result["passed"] = self._compare(val, check.operator, check.threshold)
            else:
                result["error"] = "No data"

    async def _probe_http(self, check: HypothesisCheckConfig, result: Dict[str, Any]):
        if not check.url:
            result["error"] = "url missing"
            return
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(check.url, timeout=check.timeout_seconds)
            status_passed = True
            if check.expected_status:
                status_passed = resp.status_code == check.expected_status
                result["value"] = resp.status_code
                
            body_passed = True
            if check.body_regex:
                body_passed = bool(re.search(check.body_regex, resp.text))
                
            result["passed"] = status_passed and body_passed

    async def _probe_tcp(self, check: HypothesisCheckConfig, result: Dict[str, Any]):
        if not check.host or not check.port:
            result["error"] = "host or port missing"
            return
            
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(check.host, check.port),
                timeout=check.timeout_seconds
            )
            writer.close()
            await writer.wait_closed()
            result["passed"] = True
            result["value"] = 1
        except asyncio.TimeoutError:
            result["error"] = "Timeout"
            result["passed"] = False
        except Exception as e:
            result["error"] = str(e)
            result["passed"] = False

    async def _probe_script(self, check: HypothesisCheckConfig, result: Dict[str, Any]):
        if not check.script_path:
            result["error"] = "script_path missing"
            return
            
        process = await asyncio.create_subprocess_shell(
            check.script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=check.timeout_seconds)
            result["passed"] = process.returncode == 0
            result["value"] = process.returncode
            if process.returncode != 0:
                result["error"] = stderr.decode().strip()
        except asyncio.TimeoutError:
            process.kill()
            result["error"] = "Script timeout"

    @staticmethod
    def _compare(value: float, operator: str, threshold: float) -> bool:
        if operator == "lt": return value < threshold
        if operator == "lte": return value <= threshold
        if operator == "gt": return value > threshold
        if operator == "gte": return value >= threshold
        if operator == "eq": return value == threshold
        return False


class HypothesisValidator:
    def evaluate(self, checks: list[dict[str, Any]]) -> bool:
        # Legacy stub
        return all(
            check.get("value", 0) >= check.get("threshold", 0)
            for check in checks
        )
