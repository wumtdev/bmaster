from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles

from bmaster.server import app


app.mount("/static", StaticFiles(directory="static"), name="static")

async def start():
	import bmaster.frontend.templates
