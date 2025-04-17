import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
import re
import anyio

from bmaster import sounds
from bmaster.api import api


router = APIRouter(tags=['sounds'])

SOUNDS_DIR = Path('data/sounds')

class SoundInfo(BaseModel):
	name: str
	size: int

def is_sound_name_valid(name: str) -> bool:
	return re.fullmatch(r'[a-zA-Zа-яА-Я\d_\- ]+\.[a-z\d]+', name) is not None

@router.get('/info')
async def get_sounds() -> list[SoundInfo]:
	return [
		SoundInfo(name=file.name, size=file.stat().st_size)
		for file in SOUNDS_DIR.iterdir() if file.is_file()
	]

@router.get('/file/{name}')
async def get_sound_file(name: str) -> FileResponse:
	if not is_sound_name_valid(name):
		raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Invalid file name')
	
	file_path = SOUNDS_DIR / name
	if not file_path.exists() or not file_path.is_file():
		raise HTTPException(status.HTTP_404_NOT_FOUND, 'File not found')
	
	return FileResponse(file_path)

@router.delete('/file/{name}')
async def delete_sound_file(name: str):
	if not is_sound_name_valid(name):
		raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Invalid file name')
	
	file_path = SOUNDS_DIR / name
	if not file_path.exists() or not file_path.is_file():
		raise HTTPException(status.HTTP_404_NOT_FOUND, 'File not found')
	
	os.remove(file_path)
	sounds.storage.mount_sync(name)

@router.post('/file')
async def upload_sound_file(file: UploadFile):
	name = file.filename
	if not is_sound_name_valid(name):
		raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Invalid file name')
	
	file_path = SOUNDS_DIR / name
	if file_path.exists():
		raise HTTPException(status.HTTP_409_CONFLICT, 'File with this name already exists')
	
	async with await anyio.open_file(file_path, 'wb') as f:
		await f.write(await file.read())
	sounds.storage.mount_sync(name)
