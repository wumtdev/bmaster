from uuid import UUID
from fastapi import Depends, HTTPException

from bmaster.api.auth import require_permissions
from bmaster.api.auth.users import User, UserInfo
import bmaster.icoms as icoms
from bmaster import icoms
from bmaster.api import api
from bmaster.icoms.queries import QueryAuthor


def query_author_from_user(user: UserInfo | User):
	if not isinstance(user, UserInfo):
		user = user.get_info()
	match user.type:
		case 'account':
			return QueryAuthor(
				type='account',
				name=user.name,
				label=f'#{user.id}'
			)
		case 'root':
			return QueryAuthor(
				type='root',
				name='Администратор'
			)
	return QueryAuthor(
		type='unknown',
		label='Неизвестный'
	)

class QueryNotFound(HTTPException):
	def __init__(self, id: str):
		super().__init__(status_code=404, detail=f"Query with id '{id}' not found")

@api.get('/queries/{id}', tags=['queries'])
async def get_query(id: str) -> icoms.QueryInfo:
	query = icoms.queries.get_by_id(UUID(id))
	if not query: raise QueryNotFound(id)
	return query.get_info()

@api.delete('/queries/{id}', tags=['queries'], dependencies=[
	Depends(require_permissions('bmaster.icoms.queue.manage'))
])
async def cancel_query(id: str) -> icoms.QueryInfo:
	query = icoms.queries.get_by_id(UUID(id))
	if not query: raise QueryNotFound(id)
	query.cancel()
	return query.get_info()
