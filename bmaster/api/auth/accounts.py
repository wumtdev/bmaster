from datetime import datetime, timedelta
import secrets
from typing import Annotated, Literal
from fastapi import Depends, HTTPException, status
from pydantic import AfterValidator, BaseModel, Field
from sqlalchemy import ForeignKey, inspect, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bmaster.api import api
from bmaster.api.auth import require_permissions
from bmaster.api.auth.users import User, UserInfo, UserLocalInfo
from bmaster.database import Base
from bmaster.api.auth.permissions import Role
from bmaster.api.auth.hashing import hash_password, verify_and_update_password_hash


def validate_username(name: str):
    if name.lower() == "root":
        raise ValueError()
    return name


class AccountModel(BaseModel):
    id = Annotated[str, Field(gt=0)]
    name = Annotated[
        str,
        Field(
            min_length=3,
        ),
        AfterValidator(validate_username),
    ]
    password = Annotated[str, Field(min_length=5)]


class AccountInfo(UserInfo):
    type: Literal["account"] = "account"
    id: int
    name: str
    deleted: bool = False
    role_ids: set[int]


class AccountLocalInfo(UserLocalInfo):
    type: Literal["account"] = "account"
    id: int
    name: str
    permissions: set[str]


@User.register
class Account(Base):
    """Human authorization user"""

    __tablename__ = "account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    password_hash: Mapped[str]

    roles: Mapped[list[Role]] = relationship(
        Role, secondary="account_role", lazy="joined"
    )

    def __init__(self, name: str, password: str):
        super().__init__(name=name, password_hash=hash_password(password))

    def set_password(self, new_password: str):
        self.password_hash = hash_password(new_password)

    def verify_and_update_password_hash(self, password: str) -> None:
        """Verify and update password hash if it's required. Raise exception on verification failure."""
        new_hash = verify_and_update_password_hash(self.password_hash, password)
        if new_hash is not None:
            self.password_hash = new_hash

    def get_info(self) -> AccountInfo:
        return AccountInfo(
            id=self.id,
            name=self.name,
            deleted=inspect(self).deleted,
            role_ids=map(lambda x: x.id, self.roles),
        )

    def get_local_info(self) -> AccountLocalInfo:
        return AccountLocalInfo(
            id=self.id, name=self.name, permissions=self.permissions
        )

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
    """Role assignment to account."""

    __tablename__ = "account_role"

    account_id: Mapped[int] = mapped_column(
        ForeignKey(Account.id, ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey(Role.id, ondelete="CASCADE"), primary_key=True
    )


class AccountSession(Base):
    """Authentication session of account."""

    __tablename__ = "account_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey(Account.id, ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(unique=True, index=True)
    expires_at: Mapped[datetime]
    closed: Mapped[bool] = mapped_column(default=False)

    def __init__(self, account: Account, expire_duration: timedelta):
        super().__init__(
            account_id=account.id,
            expires_at=datetime.now() + expire_duration,
            token=secrets.token_urlsafe(32),
        )

    def is_valid(self) -> bool:
        """Check if session is valid to authenticate."""
        return not self.closed and datetime.now() < self.expires_at


@api.get("/auth/accounts", tags=["auth"])
async def get_accounts() -> list[AccountInfo]:
    from bmaster.database import LocalSession

    async with LocalSession() as session:
        accounts = (await session.execute(select(Account))).scalars()
    return map(Account.get_info, accounts)


@api.get("/auth/accounts/{user_id}", tags=["auth"])
async def get_account(user_id: int) -> AccountInfo:
    from bmaster.database import LocalSession

    async with LocalSession() as session:
        user = await session.get(Account, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user.get_info()


class AccountCreateRequest(BaseModel):
    name: AccountModel.name
    password: AccountModel.password
    role_ids: set[int] = Field(default_factory=lambda: set())


@api.post(
    "/auth/accounts",
    tags=["auth"],
    dependencies=[Depends(require_permissions("bmaster.accounts.manage"))],
)
async def create_account(req: AccountCreateRequest) -> AccountInfo:
    from bmaster.database import LocalSession

    user = Account(name=req.name, password=req.password)
    async with LocalSession() as session:
        async with session.begin():
            if req.role_ids:
                roles = (
                    (
                        await session.execute(
                            select(Role).where(Role.id.in_(req.role_ids))
                        )
                    )
                    .scalars()
                    .all()
                )
                if len(roles) != len(req.role_ids):
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND, "Some roles were not found"
                    )
                user.roles = roles
            session.add(user)
        await session.refresh(user, ["roles"])
        return user.get_info()


class AccountUpdateRequest(BaseModel):
    name: AccountModel.name | None = None
    password: AccountModel.password | None = None
    role_ids: set[int] | None = None


@api.patch(
    "/auth/accounts/{user_id}",
    tags=["auth"],
    dependencies=[Depends(require_permissions("bmaster.accounts.manage"))],
)
async def update_account(user_id: int, req: AccountUpdateRequest) -> AccountInfo:
    from bmaster.database import LocalSession

    async with LocalSession() as session, session.begin():
        user = await session.get(Account, user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        new_name = req.name
        new_password = req.password
        new_role_ids = req.role_ids
        if new_role_ids is not None:
            roles = (
                (await session.execute(select(Role).where(Role.id.in_(new_role_ids))))
                .scalars()
                .all()
            )
            if len(roles) != len(new_role_ids):
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, "Some roles were not found"
                )
            user.roles = roles
        if new_name is not None:
            user.name = new_name
        if new_password is not None:
            user.set_password(new_password)
    return user.get_info()


@api.delete(
    "/auth/accounts/{user_id}",
    tags=["auth"],
    dependencies=[Depends(require_permissions("bmaster.accounts.manage"))],
)
async def delete_account(user_id: int):
    from bmaster.database import LocalSession

    async with LocalSession() as session, session.begin():
        user = await session.get(Account, user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        await session.delete(user)
    return user.get_info()
