from fastapi import HTTPException

from bmaster.api import api
import bmaster.icoms as icoms


class IcomNotFound(HTTPException):
	def __init__(self, name: str):
		super().__init__(status_code=404, detail=f"Icom with name '{name}' not found")

@api.get('/icoms/{name}', tags=['icoms'])
async def get_icom(name: str) -> icoms.IcomInfo:
	icom = icoms.get(name)
	if not icom: raise IcomNotFound(name)
	return icom.get_info()
