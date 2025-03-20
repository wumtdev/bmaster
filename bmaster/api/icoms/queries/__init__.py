from uuid import UUID
from fastapi import HTTPException

import bmaster.icoms as icoms
from bmaster import icoms
from bmaster.server import app


class QueryNotFound(HTTPException):
	def __init__(self, id: str):
		super().__init__(status_code=404, detail=f"Query with id '{id}' not found")

@app.get('/queries/{id}')
async def get_query(id: str) -> icoms.QueryInfo:
	query = icoms.queries.get_by_id(UUID(id))
	if not query: raise QueryNotFound(id)
	return query.get_info()

@app.delete('/queries/{id}')
async def cancel_query(id: str) -> icoms.QueryInfo:
	query = icoms.queries.get_by_id(UUID(id))
	if not query: raise QueryNotFound(id)
	query.cancel()
	return query.get_info()
