from fastapi import HTTPException

from bmaster.server import app
import bmaster.icoms as icoms


class IcomNotFound(HTTPException):
	def __init__(self, name: str):
		super().__init__(status_code=404, detail=f"Icom with name '{name}' not found")

@app.get('/icoms/{name}')
async def get_icom(name: str) -> icoms.IcomInfo:
	icom = icoms.get(name)
	if not icom: raise IcomNotFound(name)
	return icom.get_info()
