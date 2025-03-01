from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from pydantic import BaseModel

from bmaster import configs, logs


class SchedulingConfig(BaseModel):
	url: str

config: Optional[SchedulingConfig] = None

logger = logs.logger.getChild('scheduling')

scheduler = AsyncIOScheduler(
	logger=logger.getChild('apscheduler')
)

async def start():
	logger.info("Starting scheduler...")
	config = SchedulingConfig.model_validate(configs.main_config['scheduling'])

	scheduler.add_jobstore(
		SQLAlchemyJobStore(url=config.url)
	)
	scheduler.start()
	logger.info("Scheduler started")

async def stop():
	logger.info("Stopping scheduler...")
	scheduler.shutdown()
	logger.info("Scheduler stopped")
