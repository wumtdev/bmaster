from typing import TYPE_CHECKING
from pydantic import BaseModel
from sqlalchemy import ForeignKey, Integer, Text, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bmaster.database import Base
from bmaster.api.auth.permissions import Role


class UserInfo(BaseModel):
	id: int
	name: str
	deleted: bool = False
	role_ids: set[int]

class User(Base):
	__tablename__ = 'user'

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	name: Mapped[str] = mapped_column(Text, nullable=False)
	password_hash: Mapped[str] = mapped_column(Text, nullable=False)

	roles: Mapped[list[Role]] = relationship(
		Role,
		secondary='user_role',
		lazy='joined'
	)

	def get_info(self) -> UserInfo:
		return UserInfo(
			id=self.id,
			name=self.name,
			deleted=inspect(self).deleted,
			role_ids=map(lambda x: x.id, self.roles)
		)
	
	def set_password(self, new_password: str):
		from bmaster.api.auth import hasher
		self.password_hash = hasher.hash(new_password)
	
	def has_permissions(self, *permissions: str) -> bool:
		required_perms = set(permissions)
		for role in self.roles:
			required_perms.difference_update(role.permissions)
			if not required_perms:
				return True
		return False

class UserRole(Base):
	__tablename__ = 'user_role'

	user_id: Mapped[int] = mapped_column(ForeignKey(User.id), primary_key=True)
	role_id: Mapped[int] = mapped_column(ForeignKey(Role.id), primary_key=True)
