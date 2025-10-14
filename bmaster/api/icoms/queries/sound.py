from typing import Annotated
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from bmaster.api.auth import require_permissions, require_user
from bmaster.api.auth.users import User
from bmaster.api.icoms.queries import query_author_from_user
import bmaster.icoms as icoms
from bmaster import icoms
from bmaster.icoms.queries import SoundQuery, SoundQueryInfo
from bmaster.api import api


class PlaySoundRequest(BaseModel):
	icom_id: str
	sound_name: str
	priority: int = 0
	force: bool = False

@api.post("/queries/sound", tags=['queries'], dependencies=[
	Depends(require_permissions('bmaster.icoms.queries.sound'))
])
async def play_sound(user: Annotated[User, Depends(require_user)], request: PlaySoundRequest) -> SoundQueryInfo:
	icom = icoms.get(request.icom_id)
	if not icom: raise HTTPException(status.HTTP_404_NOT_FOUND, 'Icom not found')

	query = SoundQuery(
		icom=icom,
		sound_name=request.sound_name,
		priority=request.priority,
		force=request.force,
		author=query_author_from_user(user)
	)
	
	return query.get_info()
