from typing import Optional
from fastapi import Request
from pydantic import BaseModel

from bmaster.server import app
import bmaster.icoms as icoms
from bmaster.icoms.queries import SoundQuery


class PlaySoundRequest(BaseModel):
	icom: str
	name: str
	priority: int = 0
	force: bool = False
	duration: float = 10.0


@app.post("/icoms/play_sound")
async def play_sound(req: PlaySoundRequest):
	icom = icoms.get(req.icom)
	if not icom: 
		from fastapi import HTTPException
		raise HTTPException(status_code=404, detail="Icom not found")
	query = SoundQuery(
		name = req.name,
		priority = req.priority,
		force = req.force,
		duration = req.duration
	)
	icom.add_query(query)
