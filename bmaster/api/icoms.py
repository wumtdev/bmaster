from uuid import UUID
from pydantic import BaseModel
from fastapi import HTTPException

from bmaster.server import app
import bmaster.icoms as icoms
from bmaster.icoms.queries import SoundQuery


class PlaySoundRequest(BaseModel):
	icom: str
	name: str
	priority: int = 0
	force: bool = False


@app.post("/icoms/play_sound")
async def play_sound(req: PlaySoundRequest):
	icom = icoms.get(req.icom)
	if not icom:
		raise HTTPException(status_code=404, detail="Icom not found")
	query = SoundQuery(
		icom=icom,
		name=req.name,
		priority=req.priority,
		force=req.force
	)
	
	return {"uuid": query.id}

@app.delete('/queries/{uuid}')
async def cancel_query(uuid: str):
	query = icoms.queries.get_by_id(UUID(uuid))
	if not query:
		raise HTTPException(status_code=404, detail="Query not found")
	query.cancel()
	return {"status": "cancelled"}
