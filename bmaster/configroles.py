from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from bmaster import configs
from bmaster.logs import main_logger
from bmaster.api.auth.permissions import Role


# class RoleConfig(BaseModel):
# 	permissions: set[str]

class RolesConfig(BaseModel):
	init: bool = False
	roles: dict[str, set[str]] = Field(default_factory=lambda: dict())

config: Optional[RolesConfig] = None
logger = main_logger.getChild('configroles')

async def create_config_roles():
	global config
	config = RolesConfig.model_validate(configs.get('roles'))
	if config.init:
		logger.info('Config roles is enabled, reading roles...')
		from bmaster.database import LocalSession
		async with LocalSession() as session:
			async with session.begin():
				for role_name, permissions in config.roles.items():
					old_role = (await session.execute(select(Role).where(Role.name == role_name))).scalar()
					if old_role:
						logger.info(f'Updated existing role "{role_name}" permissions')
						old_role.permissions = permissions
					else:
						logger.info(f'Created new role "{role_name}"')
						session.add(Role(name=role_name, permissions=permissions))
		logger.info('Roles created')
	else:
		logger.info('Config roles are disabled, skipping...')
