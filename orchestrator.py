import time
import threading
from datetime import datetime
from hypothesis import SteadyStateHypothesis
from prometheus_client import PrometheusWatcher
from notifier import Notifier

class ChaosOrchestrator:
    def __init__(self, config, hypothesis, notifier):
        self.config = config
        self.hypothesis = hypothesis
        self.notifier = notifier
        self.watcher = PrometheusWatcher(config["prometheus_url"])
        self.active_experiments = {}
        self.history = []
    
    def run_experiment(self, experiment_name: str, target: str) -> dict:
        """runs a single chaos experiment on the target system"""
        
        experiment = self._get_experiment(experiment_name)
        if not experiment:
            return {"status": "error", "message": "Experiment not found"}
        
        # Шаг 1: checking steady state hypothesis
        print(f"[*] Validating steady state hypothesis...")
        if not self.hypothesis.validate():
            self.notifier.send(
                f"❌ Chaos ABORTED: System unhealthy before '{experiment_name}'",
                level="error"
            )
            return {
                "status": "aborted",
                "reason": "System unhealthy",
                "hypothesis_results": self.hypothesis.results
            }
        
        # Шаг 2: Сmetrics before
        print(f"[*] Capturing baseline metrics...")
        baseline = self.watcher.snapshot()
        
        # Шаг 3: start chaos injection
        print(f"[💥] Injecting chaos: {experiment_name} on {target}")
        chaos_start = datetime.now()
        
        thread = threading.Thread(
            target=self._execute_chaos,
            args=(experiment, target)
        )
        thread.start()
        
        # Шаг 4: monitoring during
        self._monitor_during_chaos(experiment, thread)
        
        # Шаг 5: wair for recovery
        print(f"[*] Waiting for recovery...")
        recovery_time = self._wait_for_recovery()
        
        # Шаг 6: getting metrics after 
        print(f"[*] Capturing post-chaos metrics...")
        aftermath = self.watcher.snapshot()
        
        # Шаг 7: analyze results 
        result = {
            "experiment": experiment_name,
            "target": target,
            "chaos_start": chaos_start.isoformat(),
            "recovery_time_seconds": recovery_time,
            "baseline": baseline,
            "aftermath": aftermath,
            "hypothesis_before": self.hypothesis.results,
            "verdict": self._determine_verdict(baseline, aftermath, recovery_time)
        }
        
        self.history.append(result)
        self.notifier.send(
            f"✅ Chaos '{experiment_name}' completed\n"
            f"Recovery: {recovery_time}s\n"
            f"Verdict: {result['verdict']}"
        )
        
        return result
    
    def _monitor_during_chaos(self, experiment, thread):
        """Monitoring during chaos — auto-rollback if everything goes bad"""
        degradation_limit = experiment.get("max_degradation", {})
        
        while thread.is_alive():
            time.sleep(2)
            
            # check critical metrics
            error_rate = self.watcher.get_error_rate()
            if error_rate > degradation_limit.get("error_rate", 0.2):
                self.notifier.send(
                    f"🚨 CRITICAL: Error rate {error_rate:.1%} exceeds limit! Rolling back...",
                    level="critical"
                )
                self._rollback(experiment)
                thread.join(timeout=5)
                return
            
            latency = self.watcher.get_p99_latency()
            if latency > degradation_limit.get("latency_ms", 2000):
                self.notifier.send(
                    f"⚠️ WARNING: P99 latency {latency}ms exceeds limit!",
                    level="warning"
                )
    
    def _wait_for_recovery(self) -> float:
        """wait for the system to recover after chaos injection"""
        max_wait = 300  # 5 minutesmax
        start = time.time()
        
        while time.time() - start < max_wait:
            if self.hypothesis.validate():
                return time.time() - start
            time.sleep(5)
        
        return -1  # not recovered in time
    
    def _rollback(self, experiment):
        """emergency rollback — kill chaos processes"""
        # send signal to stop on agent
        # delete files, recover iptables и т.д.
        pass
    
    def _determine_verdict(self, baseline, aftermath, recovery_time) -> str:
        """Puts down a verdict: PASS / DEGRADED / FAIL"""
        if recovery_time < 0:
            return "FAIL - Did not recover"
        if recovery_time > 120:
            return "DEGRADED - Slow recovery"
        
        # compare metrics
        if aftermath.get("error_rate", 0) > baseline.get("error_rate", 0) * 2:
            return "DEGRADED - Elevated errors"
        
        return "PASS - System resilient"