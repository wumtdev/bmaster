from abc import ABC
from typing import TYPE_CHECKING, Literal
from pydantic import BaseModel
from sqlalchemy import ForeignKey, Integer, Text, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bmaster.api import api
from bmaster.api.auth.users import User, UserInfo
from bmaster.database import Base
from bmaster.api.auth.permissions import Role


class ServiceConfig(BaseModel):
	enabled: bool
	password: str

class RootUserInfo(UserInfo):
	type: Literal['root'] = 'root'

@User.register
class RootUser:
	def get_label(self) -> str:
		return '<Root service access>'
	
	def has_permissions(self, *required_permissions) -> bool:
		# Full access
		return True
	
	def get_info(self):
		return RootUserInfo()
	
	def get_local_info(self):
		return RootUserInfo()

root = RootUser()

class ServiceInfo(BaseModel):
	enabled: bool

@api.get('/auth/service')
async def get_service_info():
	from bmaster.api.auth import config
	enabled = config.service.enabled
	return ServiceInfo(
		enabled=enabled
	)
