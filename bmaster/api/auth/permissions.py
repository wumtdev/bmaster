from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    Select,
    Text,
    and_,
    inspect,
    or_,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


from typing import Optional
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field

from sqlalchemy import select

from bmaster.api import api
from bmaster.api.auth.permissions import Role, RoleInfo

from bmaster.database import Base, TextArray


class RoleInfo(BaseModel):
    id: int
    name: str
    permissions: set[str]


class Role(Base):
    __tablename__ = "role"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    permissions: Mapped[set[str]] = mapped_column(TextArray(unique_set=True))

    def get_info(self):
        return RoleInfo(id=self.id, name=self.name, permissions=self.permissions)


class PermissionOverride(Base):
    __abstract__ = True

    role_id: Mapped[int] = mapped_column(ForeignKey(Role.id), primary_key=True)
    permission: Mapped[str] = mapped_column(Text, primary_key=True)
    state: Mapped[bool] = mapped_column(Boolean)


@api.get("/auth/roles", tags=["auth"])
async def get_roles() -> list[RoleInfo]:
    from bmaster.database import LocalSession

    async with LocalSession() as session:
        roles = (await session.execute(select(Role))).scalars().all()
    return map(lambda r: r.get_info(), roles)


@api.get("/auth/roles/{role_id}", tags=["auth"])
async def get_role(role_id: int) -> RoleInfo:
    from bmaster.database import LocalSession

    async with LocalSession() as session:
        role = await session.get(Role, role_id)
        if not role:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")
    return role.get_info()


class RoleCreateRequest(BaseModel):
    name: str
    permissions: set[str] = Field(default_factory=lambda: set())


@api.post(
    "/auth/roles",
    tags=["auth"],
    dependencies=[Depends(require_permissions("bmaster.roles.manage"))],
)
async def create_role(req: RoleCreateRequest) -> RoleInfo:
    from bmaster.database import LocalSession

    role = Role(name=req.name, permissions=req.permissions)
    async with LocalSession() as session, session.begin():
        session.add(role)
    return role.get_info()


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = None
    permissions: set[str] = Field(default_factory=lambda: set())


@api.patch(
    "/auth/roles/{role_id}",
    tags=["auth"],
    dependencies=[Depends(require_permissions("bmaster.roles.manage"))],
)
async def update_role(req: RoleUpdateRequest, role_id: int) -> RoleInfo:
    from bmaster.database import LocalSession

    async with LocalSession() as session, session.begin():
        role = session.get(Role, role_id)
        if not role:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")

        if req.name is not None:
            role.name = req.name
        if req.permissions is not None:
            role.permissions = req.permissions

    return role.get_info()


@api.delete(
    "/auth/roles/{role_id}",
    tags=["auth"],
    dependencies=[Depends(require_permissions("bmaster.roles.manage"))],
)
async def delete_role(role_id: int) -> RoleInfo:
    from bmaster.database import LocalSession

    async with LocalSession() as session, session.begin():
        role = session.get(Role, role_id)
        if not role:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")
        await session.delete(role)

    return role.get_info()
