import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from apscheduler.schedulers.background import BackgroundScheduler

backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

from services.scheduler import (
    register_market_scrape_jobs,
    run_market_close_scrape,
    run_market_open_scrape,
    run_midday_scrape,
    scheduled_job_ids,
)


class SchedulerTests(unittest.TestCase):
    def test_registers_three_fixed_daily_jobs(self):
        scheduler = BackgroundScheduler()
        register_market_scrape_jobs(scheduler)

        jobs = {job.id: job for job in scheduler.get_jobs()}

        self.assertEqual(set(jobs), set(scheduled_job_ids()))
        self.assertEqual(str(jobs["nse_market_open"].trigger.fields[5]), "9")
        self.assertEqual(str(jobs["nse_midday_update"].trigger.fields[5]), "12")
        self.assertEqual(str(jobs["nse_market_close"].trigger.fields[5]), "15")
        for job in jobs.values():
            self.assertEqual(str(job.trigger.fields[6]), "0")
            self.assertIn("Africa/Nairobi", str(job.trigger.timezone))

    def test_scheduled_job_functions_execute_expected_snapshots(self):
        with patch("services.scheduler.scrape_and_update_cache") as scrape:
            scrape.return_value = {"status": "success"}

            run_market_open_scrape()
            run_midday_scrape()
            run_market_close_scrape()

        scrape.assert_any_call("market_opening_snapshot")
        scrape.assert_any_call("midday_market_update")
        scrape.assert_any_call("market_closing_snapshot")
        self.assertEqual(scrape.call_count, 3)


if __name__ == "__main__":
    unittest.main()
