from pydantic import BaseModel
from sqlalchemy import Boolean, ForeignKey, Integer, Select, Text, and_, inspect, or_, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bmaster.database import Base, TextArray


class RoleInfo(BaseModel):
	id: int
	name: str
	permissions: set[str]

class Role(Base):
	__tablename__ = 'role'
	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	name: Mapped[str] = mapped_column(Text)
	permissions: Mapped[set[str]] = mapped_column(TextArray(unique_set=True))

	def get_info(self):
		return RoleInfo(
			id=self.id,
			name=self.name,
			permissions=self.permissions
		)


class PermissionOverride(Base):
	__abstract__ = True

	role_id: Mapped[int] = mapped_column(ForeignKey(Role.id), primary_key=True)
	permission: Mapped[str] = mapped_column(Text, primary_key=True)
	state: Mapped[bool] = mapped_column(Boolean)
