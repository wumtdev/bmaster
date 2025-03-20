import numpy as np
from pydantic import BaseModel, ValidationError
from fastapi import File, Form, HTTPException, UploadFile
from wauxio import Audio

from bmaster.api.icoms import IcomNotFound
from bmaster.server import app
import bmaster.icoms as icoms
from bmaster.icoms.queries import AudioQuery, QueryInfo


class APIAudioRequest(BaseModel):
	icom: str
	priority: int = 0
	force: bool = False
	rate: int
	channels: int

@app.post('/queries/audio')
async def play_audio(
	request: str = Form(..., media_type='application/json'),
	audio: UploadFile = File(...)
) -> QueryInfo:
	try: request: APIAudioRequest = APIAudioRequest.model_validate_json(request)
	except ValidationError as e: raise HTTPException(422, e.errors())

	icom = icoms.get(request.icom)
	if not icom: raise IcomNotFound(request.icom)

	channels = request.channels
	# TODO: Implement multi-channels
	if channels != 1: raise HTTPException(400, 'Only 1 channel supported')

	audio_bytes = await audio.read()
	try: audio_data = np.frombuffer(audio_bytes, dtype=np.float32)
	except: raise HTTPException(400, 'Failed to decode audio data')

	audio = Audio(
		data=audio_data,
		rate=request.rate
	)

	query = AudioQuery(
		icom=icom,
		audio=audio,
		priority=request.priority,
		force=request.force
	)
	
	return query.get_info()