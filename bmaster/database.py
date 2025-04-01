from typing import Optional
from pydantic import BaseModel
from sqlalchemy import TypeDecorator, JSON
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from bmaster import configs, logs


class DatabaseConfig(BaseModel):
	url: str

config: Optional[DatabaseConfig] = None

logger = logs.logger.getChild('database')

engine: Optional[AsyncEngine] = None
LocalSession: sessionmaker[AsyncSession] = None

Base = declarative_base()


async def start():
	global config, engine, LocalSession
	config = DatabaseConfig.model_validate(configs.main_config['database'])

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

async def update_models():
	global Base
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)

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
