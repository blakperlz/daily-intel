"""
APScheduler job definitions.
Reads cron schedules from config.yaml.
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from utils.config_loader import get_config
from digest_runner import run_digest


def start_scheduler():
    cfg = get_config()["digest"]
    tz = pytz.timezone(cfg.get("timezone", "America/New_York"))
    scheduler = BlockingScheduler(timezone=tz)

    # Morning brief
    morning = cfg.get("morning_cron", "0 6 * * 1-5")
    scheduler.add_job(
        lambda: run_digest("daily"),
        CronTrigger.from_crontab(morning, timezone=tz),
        id="morning_brief",
        name="Morning Intelligence Brief",
        misfire_grace_time=900,  # 15 min grace
    )

    # Evening recap
    evening = cfg.get("evening_cron", "0 18 * * 1-5")
    scheduler.add_job(
        lambda: run_digest("daily"),
        CronTrigger.from_crontab(evening, timezone=tz),
        id="evening_recap",
        name="Evening Intelligence Recap",
        misfire_grace_time=900,
    )

    # Weekly deep dive
    weekly = cfg.get("weekly_cron", "0 18 * * 0")
    scheduler.add_job(
        lambda: run_digest("weekly"),
        CronTrigger.from_crontab(weekly, timezone=tz),
        id="weekly_summary",
        name="Weekly Intelligence Summary",
        misfire_grace_time=3600,
    )

    print("[scheduler] Jobs registered:")
    for job in scheduler.get_jobs():
        print(f"  • {job.name} — next run: {job.next_run_time}")

    scheduler.start()
