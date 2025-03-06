from uuid import UUID
from pydantic import BaseModel
from fastapi import HTTPException

from bmaster.server import app
import bmaster.icoms as icoms
from bmaster.icoms.queries import QueryStatus, SoundQuery


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
		sound_name=req.name,
		priority=req.priority,
		force=req.force
	)
	
	return {'uuid': query.id}

@app.get('/icoms/{name}')
async def get_icom(name: str) -> icoms.IcomInfo:
	icom = icoms.get(name)
	if not icom:
		raise HTTPException(status_code=404, detail='Icom not found')
	return icom.get_info()


class QueryNotFound(HTTPException):
	def __init__(self, id: str):
		super().__init__(status_code=404, detail=f"Query with id '{id}' not found")

@app.get('/queries/{id}')
async def get_query(id: str) -> icoms.QueryInfo:
	query = icoms.queries.get_by_id(UUID(id))
	if not query: raise QueryNotFound(id)
	return query.get_info()

@app.delete('/queries/{id}')
async def cancel_query(id: str):
	query = icoms.queries.get_by_id(UUID(id))
	if not query: raise QueryNotFound(id)
	query.cancel()
	return {'status': QueryStatus.CANCELLED}
