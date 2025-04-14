from typing import Annotated
from fastapi import Depends, HTTPException, status

from bmaster.api import api
from bmaster.api.auth import require_user
from bmaster.api.auth.users import Account
from bmaster.api.icoms.auth import has_icom_permissions
import bmaster.icoms as icoms


@api.get('/icoms/{icom_id}', tags=['icoms'])
async def get_icom(icom_id: str, user: Annotated[Account, Depends(require_user)]) -> icoms.IcomInfo:
	icom = icoms.get(icom_id)
	if not icom: raise HTTPException(status.HTTP_404_NOT_FOUND, 'Icom not found')
	if not await has_icom_permissions(icom, user, 'bmaster.icoms.read'):
		raise HTTPException(status.HTTP_404_NOT_FOUND, 'Icom not found')
	return icom.get_info()

@api.get('/icoms', tags=['icoms'])
async def get_icoms(user: Annotated[Account, Depends(require_user)]) -> dict[str, icoms.IcomInfo]:
	res = dict()
	for icom in icoms._icoms_map.values():
		if not icom: raise HTTPException(status.HTTP_404_NOT_FOUND, 'Icom not found')
		if await has_icom_permissions(icom, user, 'bmaster.icoms.read'):
			res[icom.id] = icom.get_info()
	return res
