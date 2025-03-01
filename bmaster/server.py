import asyncio
from asyncio import Task
from typing import Optional
from fastapi import FastAPI
import uvicorn

from bmaster import logs


logger = logs.logger.getChild('server')

app = FastAPI(
	title="bmaster"
)

serving: Optional[Task] = None

async def start():
	global serving
	logger.info("Starting uvicorn...")
	config = uvicorn.Config(
		app,
		host="127.0.0.1",
		port=8000,
		loop="asyncio",
		log_config=None
	)
	server = uvicorn.Server(config)
	serving = asyncio.create_task(server.serve())
	logger.info("Uvicorn started")
