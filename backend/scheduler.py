from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import load_platform_config


class ChaosScheduler:
    def __init__(self, orchestrator, config_path: str | Path | None = None):
        self.orchestrator = orchestrator
        self.scheduler = BackgroundScheduler()
        self.config_path = Path(config_path or Path(__file__).with_name("config.yaml"))
        self.config = self._load_config()
        self._load_schedules()

    def _load_config(self):
        return load_platform_config(self.config_path)

    def _load_schedules(self):
        for schedule in self.config.schedules:
            self.scheduler.add_job(
                func=self.orchestrator.run_experiment,
                trigger=CronTrigger.from_crontab(schedule.cron),
                args=[schedule.experiment, schedule.target],
                id=schedule.name,
                name=schedule.name,
            )

    def start(self):
        self.scheduler.start()

    def list_jobs(self):
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time),
            }
            for job in self.scheduler.get_jobs()
        ]


Scheduler = ChaosScheduler
