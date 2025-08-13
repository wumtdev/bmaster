from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Text, TypeDecorator, JSON
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from bmaster import configs, logs


class DatabaseConfig(BaseModel):
	url: str

config: Optional[DatabaseConfig] = None

logger = logs.main_logger.getChild('database')

engine: Optional[AsyncEngine] = None
LocalSession: sessionmaker[AsyncSession] = None

Base = declarative_base()


async def start():
	global config, engine, LocalSession
	
	logger.info('Starting database...')
	
	config = DatabaseConfig.model_validate(configs.get('database'))

	logger.info('Initializing engine...')
	engine = create_async_engine(
		url=config.url
	)
	logger.info('Engine initialized')

	logger.info('Initializing session maker...')
	LocalSession = sessionmaker(
		bind=engine,
		class_=AsyncSession,
		expire_on_commit=False
	)
	logger.info('Session maker initialized')
	
	logger.info('Database started')

async def update_models():
	global Base

	logger.info('Updating models...')

	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)

	logger.info('Models updated')

async def stop():
	logger.info('Stopping database...')
	await engine.dispose()
	logger.info('Database stopped')


class JSONModel(TypeDecorator):
	impl = JSON

	def __init__(self, pydantic_model: type[BaseModel], *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.pydantic_model = pydantic_model

	def process_bind_param(self, value: BaseModel | None, dialect):
		return value.model_dump() if value is not None else None

	def process_result_value(self, value: dict | None, dialect):
		return self.pydantic_model.model_validate(value) if value is not None else None

class TextArray(TypeDecorator):
	impl = Text
	
	unique_set: bool

	def __init__(self, unique_set: bool = False, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.unique_set = unique_set

	def process_bind_param(self, value: list[str] | None, dialect):
		# TODO: Escape ',' chars
		return ','.join(value) if value is not None else None
	
	def process_result_value(self, value: str | None, dialect):
		if not value: return None
		res = value.split(',')
		if self.unique_set:
			res = set(res)
		return res
