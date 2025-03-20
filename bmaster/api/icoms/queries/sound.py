from pydantic import BaseModel

from bmaster.api.icoms import IcomNotFound
import bmaster.icoms as icoms
from bmaster import icoms
from bmaster.icoms.queries import SoundQuery, SoundQueryInfo
from bmaster.server import app


class APISoundRequest(BaseModel):
	icom: str
	name: str
	priority: int = 0
	force: bool = False

@app.post("/queries/sound")
async def play_sound(request: APISoundRequest) -> SoundQueryInfo:
	icom = icoms.get(request.icom)
	if not icom: raise IcomNotFound(request.icom)

	query = SoundQuery(
		icom=icom,
		sound_name=request.name,
		priority=request.priority,
		force=request.force
	)
	
	return query.get_info()
