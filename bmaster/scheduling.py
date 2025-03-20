from datetime import datetime
from typing import Mapping, Optional, Self, Type, Union
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from pydantic import BaseModel, Field, field_validator, model_validator, validator

from bmaster import configs, logs


class SchedulingConfig(BaseModel):
	url: str

config: Optional[SchedulingConfig] = None

logger = logs.logger.getChild('scheduling')

scheduler = AsyncIOScheduler(
	logger=logger.getChild('apscheduler'),
	executors={
		'default': AsyncIOExecutor()
	}
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


trigger_type_map: Mapping[str, Type['JobTrigger']] = dict()

class JobTrigger(BaseModel):
	type: str
	timezone: Optional[str] = None

	def job_kwargs(self) -> dict:
		raise NotImplementedError()

	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)
		if hasattr(cls, 'type'):
			event_type = cls.model_fields['type'].default
			trigger_type_map[event_type] = cls

	@model_validator(mode='after')
	def resolve_event_type(self: Self) -> Self:
		if type(self) != Self: return self
		model = trigger_type_map.get(self.type, None)
		if model:
			return model.model_validate(self)

# --- Date Trigger ---
class DateTrigger(JobTrigger):
	type: str = Field(default="date", frozen=True)
	run_date: Union[datetime, str] = Field(default_factory=datetime.now)

	@field_validator("run_date", mode="before")
	@classmethod
	def parse_run_date(cls, v: Union[str, datetime]) -> datetime:
		if isinstance(v, str):
			return datetime.fromisoformat(v)
		return v

	def job_kwargs(self) -> dict:
		return {
			"trigger": self.type,  # Include trigger type
			"run_date": self.run_date,
			"timezone": self.timezone
		}

# --- Interval Trigger ---
class IntervalTrigger(JobTrigger):
	type: str = Field(default="interval", frozen=True)
	weeks: int = 0
	days: int = 0
	hours: int = 0
	minutes: int = 0
	seconds: int = 0
	start_date: Optional[Union[datetime, str]] = None
	end_date: Optional[Union[datetime, str]] = None

	@field_validator("start_date", "end_date", mode="before")
	@classmethod
	def parse_datetime(cls, v: Union[str, datetime, None]) -> Union[datetime, None]:
		if isinstance(v, str):
			return datetime.fromisoformat(v)
		return v

	@model_validator(mode="after")
	def check_interval(self) -> "IntervalTrigger":
		intervals = ["weeks", "days", "hours", "minutes", "seconds"]
		if not any(getattr(self, field) > 0 for field in intervals):
			raise ValueError("At least one interval (e.g., minutes=5) must be set")
		return self

	def job_kwargs(self) -> dict:
		return {
			"trigger": self.type,  # Include trigger type
			"weeks": self.weeks,
			"days": self.days,
			"hours": self.hours,
			"minutes": self.minutes,
			"seconds": self.seconds,
			"start_date": self.start_date,
			"end_date": self.end_date,
			"timezone": self.timezone
		}

# --- Cron Trigger ---
class CronTrigger(JobTrigger):
	type: str = Field(default="cron", frozen=True)
	year: Union[str, int] = "*"
	month: Union[str, int] = "*"
	day: Union[str, int] = "*"
	week: Union[str, int] = "*"
	day_of_week: Union[str, int] = "*"
	hour: Union[str, int] = "*"
	minute: Union[str, int] = "*"
	second: Union[str, int] = "0"
	start_date: Optional[Union[datetime, str]] = None
	end_date: Optional[Union[datetime, str]] = None

	@field_validator("start_date", "end_date", mode="before")
	@classmethod
	def parse_datetime(cls, v: Union[str, datetime, None]) -> Union[datetime, None]:
		if isinstance(v, str):
				return datetime.fromisoformat(v)
		return v

	def job_kwargs(self) -> dict:
		return {
			"trigger": self.type,  # Include trigger type
			"year": self.year,
			"month": self.month,
			"day": self.day,
			"week": self.week,
			"day_of_week": self.day_of_week,
			"hour": self.hour,
			"minute": self.minute,
			"second": self.second,
			"start_date": self.start_date,
			"end_date": self.end_date,
			"timezone": self.timezone
		}
