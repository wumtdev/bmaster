from typing import Annotated
import numpy as np
from pydantic import BaseModel, ValidationError
from fastapi import Depends, File, Form, HTTPException, UploadFile, status
from wauxio import Audio

from bmaster.api import api
from bmaster.api.auth import require_user
from bmaster.api.auth.users import User
from bmaster.api.icoms.queries import query_author_from_user
import bmaster.icoms as icoms
from bmaster.icoms.queries import AudioQuery, QueryInfo


class APIAudioRequest(BaseModel):
	icom: str
	priority: int = 0
	force: bool = False
	rate: int
	channels: int

@api.post('/queries/audio', tags=['queries'])
async def play_audio(
	user: Annotated[User, Depends(require_user)],
	request: str = Form(..., media_type='application/json'),
	audio: UploadFile = File(...)
) -> QueryInfo:
	try: request: APIAudioRequest = APIAudioRequest.model_validate_json(request)
	except ValidationError as e:
		raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, e.errors())

	icom = icoms.get(request.icom)
	if not icom:
		raise HTTPException(status.HTTP_404_NOT_FOUND, 'Icom not found')

	channels = request.channels
	# TODO: Implement multi-channels
	if channels != 1:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Only 1 channel supported')

	audio_bytes = await audio.read()
	try: audio_data = np.frombuffer(audio_bytes, dtype=np.float32)
	except:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Failed to decode audio data')

	audio = Audio(
		data=audio_data,
		rate=request.rate
	)

	query = AudioQuery(
		icom=icom,
		audio=audio,
		priority=request.priority,
		force=request.force,
		author=query_author_from_user(user)
	)
	
	return query.get_info()