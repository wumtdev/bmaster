from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from bmaster import logs


logger = logs.logger.getChild('scheduling')

jobstores = {
	'default': SQLAlchemyJobStore(url='sqlite:///data/scheduler.db')
}

scheduler = AsyncIOScheduler(
	jobstores=jobstores,
	logger=logger.getChild('apscheduler')
)

async def start():
	logger.info("Starting scheduler...")
	scheduler.start()
	logger.info("Scheduler started")

async def stop():
	logger.info("Stopping scheduler...")
	scheduler.shutdown()
	logger.info("Scheduler stopped")
