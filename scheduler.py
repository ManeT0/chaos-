from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import yaml

class ChaosScheduler:
    def __init__(self, orchestrator, config_path="config.yaml"):
        self.orchestrator = orchestrator
        self.scheduler = BackgroundScheduler()
        
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self._load_schedules()
    
    def _load_schedules(self):
        """Loads the schedule from the config"""
        for schedule in self.config.get("schedules", []):
            self.scheduler.add_job(
                func=self.orchestrator.run_experiment,
                trigger=CronTrigger.from_crontab(schedule["cron"]),
                args=[schedule["experiment"], schedule["target"]],
                id=schedule["name"],
                name=schedule["name"]
            )
    
    def start(self):
        self.scheduler.start()
        print("[*] Chaos Scheduler started")
    
    def list_jobs(self):
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time)
            }
            for job in self.scheduler.get_jobs()
        ]