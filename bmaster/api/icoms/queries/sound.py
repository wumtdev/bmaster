from fastapi import HTTPException, status
from pydantic import BaseModel

import bmaster.icoms as icoms
from bmaster import icoms
from bmaster.icoms.queries import SoundQuery, SoundQueryInfo
from bmaster.api import api


class APISoundRequest(BaseModel):
	icom: str
	name: str
	priority: int = 0
	force: bool = False

@api.post("/queries/sound", tags=['queries'])
async def play_sound(request: APISoundRequest) -> SoundQueryInfo:
	icom = icoms.get(request.icom)
	if not icom: raise HTTPException(status.HTTP_404_NOT_FOUND, 'Icom not found')

	query = SoundQuery(
		icom=icom,
		sound_name=request.name,
		priority=request.priority,
		force=request.force
	)
	
	return query.get_info()
