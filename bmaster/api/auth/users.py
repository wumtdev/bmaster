from abc import ABC
from typing import TYPE_CHECKING, Literal
from pydantic import BaseModel
from sqlalchemy import ForeignKey, Integer, Text, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bmaster.database import Base
from bmaster.api.auth.permissions import Role


class UserInfo(BaseModel):
	type: str

class UserLocalInfo(BaseModel):
	type: str

class User(ABC):
	def get_label(self) -> str:
		pass

	def has_permission(self, *permissions: str) -> bool:
		pass

	def get_info(self) -> UserInfo:
		pass

	def get_local_info(self) -> UserLocalInfo:
		pass


class AccountInfo(UserInfo):
	type: Literal['account'] = 'account'
	id: int
	name: str
	deleted: bool = False
	role_ids: set[int]

class AccountLocalInfo(UserLocalInfo):
	type: Literal['account'] = 'account'
	id: int
	name: str
	permissions: set[str]

@User.register
class Account(Base):
	__tablename__ = 'account'

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	name: Mapped[str] = mapped_column(Text, nullable=False)
	password_hash: Mapped[str] = mapped_column(Text, nullable=False)

	roles: Mapped[list[Role]] = relationship(
		Role,
		secondary='account_role',
		lazy='joined'
	)

	def get_info(self) -> AccountInfo:
		return AccountInfo(
			id=self.id,
			name=self.name,
			deleted=inspect(self).deleted,
			role_ids=map(lambda x: x.id, self.roles)
		)
	
	def get_local_info(self) -> AccountLocalInfo:
		return AccountLocalInfo(
			id=self.id,
			name=self.name,
			permissions=self.permissions
		)
	
	def set_password(self, new_password: str):
		from bmaster.api.auth import hasher
		self.password_hash = hasher.hash(new_password)
	
	@property
	def permissions(self) -> set[str]:
		perms = set()
		for role in self.roles:
			perms.update(role.permissions)
		return perms

	def has_permissions(self, *permissions: str) -> bool:
		return not set(permissions).difference(self.permissions)
	
	def get_label(self) -> str:
		return f'<User "{self.name}" #{self.id}>'

class AccountRole(Base):
	__tablename__ = 'account_role'

	account_id: Mapped[int] = mapped_column(ForeignKey(Account.id), primary_key=True)
	role_id: Mapped[int] = mapped_column(ForeignKey(Role.id), primary_key=True)
