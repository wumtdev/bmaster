from sqlalchemy import Boolean, ForeignKey, Integer, Select, Text, and_, inspect, or_, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bmaster.api.auth.permissions import PermissionOverride, Role
from bmaster.api.auth.service import RootUser
from bmaster.api.auth.users import Account
import bmaster.icoms as icoms


class IcomPermissionOverride(PermissionOverride):
	__tablename__ = 'icom_permission_override'

	icom_id: Mapped[str] = mapped_column(Text, primary_key=True)


async def has_icom_permissions(icom: icoms.Icom, user_or_roles: Account | int | list[Role], *required_perms: str) -> bool:

	if isinstance(user_or_roles, RootUser): return True
	if isinstance(user_or_roles, Account):
		user_or_roles = user_or_roles.id
	
	required_perms = set(required_perms)

	from bmaster.database import LocalSession
	async with LocalSession() as session, session.begin():
		if type(user_or_roles) == int:
			user_or_roles = (await session.get(Account, user_or_roles)).roles
		roles: list[Role] = user_or_roles
		
		for role in roles:
			role_perms = role.permissions.copy()
			overrides = (await session.execute(
				select(IcomPermissionOverride).where(
					IcomPermissionOverride.icom_id == icom.id,
					IcomPermissionOverride.role_id == role.id
				)
			)).scalars()
			for override in overrides:
				if override.state:
					role_perms.add(override.permission)
				else:
					role_perms.discard(override.permission)
			
			required_perms.difference_update(role_perms)
			if not required_perms:
				return True
	
	return False
