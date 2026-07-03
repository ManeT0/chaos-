import paramiko
import yaml
import time
import json
from datetime import datetime
from reporter import generate_report

class ChaosRunner:
    def __init__(self, config_path="config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.results = []
        self.ssh_clients = {}
    
    def connect(self, target):
        """Connect via SSH to the target"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=target["host"],
            username=target["user"],
            key_filename=target.get("key_path", "~/.ssh/id_rsa")
        )
        return client
    
    def capture_metrics(self, client):
        """metrics capture after and before chaos injection"""
        cmd = """
        echo "CPU: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2+$4}')%"
        echo "MEM: $(free -m | awk 'NR==2{printf \"%.1f%%\", $3*100/$2}')" 
        echo "DISK: $(df -h / | awk 'NR==2{print $5}')"
        echo "UPTIME: $(uptime -p)"
        """
        stdin, stdout, stderr = client.exec_command(cmd)
        return stdout.read().decode()
    
    def execute_experiment(self, target, experiment):
        """one experiment execution"""
        print(f"\n[▶] Running: {experiment['name']}")
        client = self.connect(target)
        
        # before
        print("   📊 Snapshot BEFORE...")
        before = self.capture_metrics(client)
        
        # inject chaos
        print(f"   💥 Injecting chaos: {experiment['command']}")
        stdin, stdout, stderr = client.exec_command(experiment["command"])
        chaos_output = stdout.read().decode()
        
        # time to wait for the chaos effect to take place
        duration = experiment.get("duration", 30)
        print(f"   ⏳ Waiting {duration}s...")
        time.sleep(duration)
        
        # AFTER
        print("   📊 Snapshot AFTER...")
        after = self.capture_metrics(client)
        
        client.close()
        
        # save results
        result = {
            "experiment": experiment["name"],
            "target": target["host"],
            "time": datetime.now().isoformat(),
            "before": before,
            "after": after,
            "chaos_output": chaos_output
        }
        self.results.append(result)
        return result
    
    def run(self):
        """run all experiments defined in the config"""
        targets = self.config["targets"]
        
        for scenario in self.config["scenarios"]:
            for target_name in scenario["targets"]:
                target = targets[target_name]
                self.execute_experiment(target, scenario)
        
        # generate report
        report_path = generate_report(self.results, self.config)
        print(f"\n✅ Report saved: {report_path}")
        return self.results

if __name__ == "__main__":
    runner = ChaosRunner("config.yaml")
    runner.run()