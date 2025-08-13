from datetime import datetime
from typing import Any, Coroutine, Literal, Optional, Self, Type, Union
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from pydantic import BaseModel, Field, ModelWrapValidatorHandler, field_validator, model_validator

from bmaster import configs, logs


class SchedulingConfig(BaseModel):
	url: str

config: Optional[SchedulingConfig] = None

logger = logs.main_logger.getChild('scheduling')

scheduler = AsyncIOScheduler(
	logger=logger.getChild('apscheduler'),
	executors={
		'default': AsyncIOExecutor()
	}
)

async def start():
	logger.info('Starting scheduler...')
	config = SchedulingConfig.model_validate(configs.main_config['scheduling'])

	scheduler.add_jobstore(
		SQLAlchemyJobStore(url=config.url),
		alias='default'
	)
	scheduler.add_jobstore(
		MemoryJobStore(),
		alias='temp'
	)
	scheduler.start()
	logger.info('Scheduler started')

async def stop():
	logger.info('Stopping scheduler...')
	scheduler.shutdown()
	logger.info('Scheduler stopped')


TRIGGER_REGISTRY: dict[str, Type['JobTrigger']] = {}

def register_trigger(cls: Type['JobTrigger']) -> Type['JobTrigger']:
	'''Decorator to register trigger type'''
	type_field = cls.model_fields.get('type', None)
	if not type_field:
		raise ValueError('Trigger must have \'type\' field')
	TRIGGER_REGISTRY[type_field.default] = cls  # type: ignore
	return cls

class JobTrigger(BaseModel):
	'''Base trigger model'''

	type: str = Field(..., description='Trigger type discriminator')
	timezone: Optional[str] = None

	def job_kwargs(self) -> Coroutine[Any, Any, None]:
		raise NotImplementedError()
	
	@model_validator(mode='wrap')
	@classmethod
	def validate_type(cls, data: Any, handler: ModelWrapValidatorHandler[Self]) -> Self:
		trigger = handler(data)
		if cls is not JobTrigger: return trigger
		trigger_type = trigger.type
		trigger_class = TRIGGER_REGISTRY.get(trigger_type, None)
		if not trigger_class:
			raise ValueError(f'Unknown trigger type: {trigger_type}')
		
		return trigger_class.model_validate(data)

# --- Date Trigger ---
@register_trigger
class DateTrigger(JobTrigger):
	type: Literal['date'] = 'date'
	run_date: Union[datetime, str] = Field(default_factory=datetime.now)

	@field_validator('run_date', mode='before')
	@classmethod
	def parse_run_date(cls, v: Union[str, datetime]) -> datetime:
		if isinstance(v, str):
			return datetime.fromisoformat(v)
		return v

	def job_kwargs(self) -> dict:
		return {
			'trigger': self.type,  # Include trigger type
			'run_date': self.run_date,
			'timezone': self.timezone
		}

# --- Interval Trigger ---
@register_trigger
class IntervalTrigger(JobTrigger):
	type: Literal['interval'] = 'interval'
	weeks: int = 0
	days: int = 0
	hours: int = 0
	minutes: int = 0
	seconds: int = 0
	start_date: Optional[Union[datetime, str]] = None
	end_date: Optional[Union[datetime, str]] = None

	@field_validator('start_date', 'end_date', mode='before')
	@classmethod
	def parse_datetime(cls, v: Union[str, datetime, None]) -> Union[datetime, None]:
		if isinstance(v, str):
			return datetime.fromisoformat(v)
		return v

	@model_validator(mode='after')
	def check_interval(self) -> 'IntervalTrigger':
		intervals = ['weeks', 'days', 'hours', 'minutes', 'seconds']
		if not any(getattr(self, field) > 0 for field in intervals):
			raise ValueError('At least one interval (e.g., minutes=5) must be set')
		return self

	def job_kwargs(self) -> dict:
		return {
			'trigger': self.type,  # Include trigger type
			'weeks': self.weeks,
			'days': self.days,
			'hours': self.hours,
			'minutes': self.minutes,
			'seconds': self.seconds,
			'start_date': self.start_date,
			'end_date': self.end_date,
			'timezone': self.timezone
		}

# --- Cron Trigger ---
@register_trigger
class CronTrigger(JobTrigger):
	type: Literal['cron'] = 'cron'
	year: Union[str, int] = '*'
	month: Union[str, int] = '*'
	day: Union[str, int] = '*'
	week: Union[str, int] = '*'
	day_of_week: Union[str, int] = '*'
	hour: Union[str, int] = '*'
	minute: Union[str, int] = '*'
	second: Union[str, int] = '0'
	start_date: Optional[Union[datetime, str]] = None
	end_date: Optional[Union[datetime, str]] = None

	@field_validator('start_date', 'end_date', mode='before')
	@classmethod
	def parse_datetime(cls, v: Union[str, datetime, None]) -> Union[datetime, None]:
		if isinstance(v, str):
				return datetime.fromisoformat(v)
		return v

	def job_kwargs(self) -> dict:
		return {
			'trigger': self.type,  # Include trigger type
			'year': self.year,
			'month': self.month,
			'day': self.day,
			'week': self.week,
			'day_of_week': self.day_of_week,
			'hour': self.hour,
			'minute': self.minute,
			'second': self.second,
			'start_date': self.start_date,
			'end_date': self.end_date,
			'timezone': self.timezone
		}
