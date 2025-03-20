import asyncio
from asyncio import Task
from typing import Optional
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
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

@app.get('/remote', response_class=HTMLResponse)
async def remote_get():
	with open('remote.html', 'r') as file:
		return file.read()
	
@app.get('/listen', response_class=HTMLResponse)
async def listen_get():
	with open('listen.html', 'r') as file:
		return file.read()

