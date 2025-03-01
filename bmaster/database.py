from typing import Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column

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
