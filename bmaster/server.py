import asyncio
from asyncio import Task
from typing import Optional
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from bmaster import logs


logger = logs.logger.getChild('server')

app = FastAPI(
	title="bmaster"
)

origins = [
	"*",
]

app.add_middleware(
	CORSMiddleware,
	allow_origins=origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
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

@app.get('/remote', response_class=HTMLResponse, tags=["html"])
async def remote_get():
	with open('remote.html', 'r') as file:
		return file.read()
	
@app.get('/listen', response_class=HTMLResponse, tags=["html"])
async def listen_get():
	with open('listen.html', 'r') as file:
		return file.read()

