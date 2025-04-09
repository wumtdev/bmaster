from sqlalchemy import Boolean, ForeignKey, Integer, Select, Text, and_, inspect, or_, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bmaster.database import Base, TextArray


class Role(Base):
	__tablename__ = 'role'
	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	name: Mapped[str] = mapped_column(Text)
	permissions: Mapped[set[str]] = mapped_column(TextArray(unique_set=True))


class PermissionOverride(Base):
	__abstract__ = True

	permission: Mapped[str] = mapped_column(Text)
	state: Mapped[bool] = mapped_column(Boolean)
