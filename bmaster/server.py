import asyncio
from asyncio import Task
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

cert_path = Path('data/cert.pem')
key_path = Path('data/key.pem')

async def start():
	global serving
	logger.info("Starting uvicorn...")
	config = uvicorn.Config(
		app,
		host="0.0.0.0",
		port=8000,
		loop="asyncio",
		log_config=None
	)
	if cert_path.exists() and key_path.exists():
		config.ssl_keyfile = key_path
		config.ssl_certfile = cert_path
	server = uvicorn.Server(config)
	serving = asyncio.create_task(server.serve())
	logger.info("Uvicorn started")

	# Serve React SPA for any other path
	@app.get("/{full_path:path}")
	async def serve_spa(request: Request, full_path: str):
		if not index_path.exists():
			return HTMLResponse("""
				<h1>React App Not Built</h1>
				<p>Run 'npm run build' in client directory first</p>
			""", status_code=404)
		
		return FileResponse(index_path)


# Serve static files from React build
app.mount('/static', StaticFiles(directory='static'), name='static')
index_path = Path('static/index.html')


