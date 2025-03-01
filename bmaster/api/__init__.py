from fastapi import APIRouter

from bmaster.server import app


api = APIRouter()
app.include_router(api)
