from apscheduler.schedulers.blocking import BlockingScheduler
from betus_scraper import main as scrape_main

def scheduled_scrape():
    print("Starting scheduled scrape...")
    scrape_main()
    print("Scheduled scrape completed.")

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_scrape, 'interval', hours=1)
    print("Scheduler started. Press Ctrl+C to exit.")
    scheduler.start()