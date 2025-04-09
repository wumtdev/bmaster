from typing import Annotated, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, ValidationError

from passlib.context import CryptContext
import jwt
from sqlalchemy import ScalarSelect, select

from bmaster import configs, logs
from bmaster.api import api
from bmaster.api.auth.users import User, UserInfo


class JwtConfig(BaseModel):
	secret_key: str
	algorithm: str
	expire_minutes: int

class HasherConfig(BaseModel):
	schemas: str

class AuthConfig(BaseModel):
	jwt: JwtConfig
	hasher: HasherConfig

config: Optional[AuthConfig] = None

logger = logs.logger.getChild('auth')

hasher: Optional[CryptContext] = None
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='/api/auth/login')


def jwt_encode(data: Any) -> str:
	return jwt.encode(
		data,
		key=config.jwt.secret_key,
		algorithm=config.jwt.algorithm
	)

def jwt_decode(token: str):
	return jwt.decode(
		jwt=token,
		key=config.jwt.secret_key,
		algorithms=[config.jwt.algorithm]
	)


def get_bearer_jwt(token: Annotated[str, Depends(oauth2_bearer)]) -> Any:
	try:
		return jwt_decode(token)
	except jwt.InvalidTokenError:
		raise HTTPException(
			status.HTTP_401_UNAUTHORIZED, 'Could not validate credentials',
			headers={'WWW-Authenticate': 'Bearer'}
		)

class Token(BaseModel):
	access_token: str
	token_type: str

class AuthToken(BaseModel):
	user_id: int

	def get_user(self) -> ScalarSelect[User]:
		return select(User).where(User.id == self.user_id)

def get_auth_token(jwt_data: Annotated[Any, Depends(get_bearer_jwt)]):
	try:
		return AuthToken.model_validate(jwt_data)
	except ValidationError:
		raise HTTPException(
			status.HTTP_401_UNAUTHORIZED, 'Could not validate credentials',
			headers={'WWW-Authenticate': 'Bearer'}
		)

async def get_user(auth_token: Annotated[AuthToken, Depends(get_auth_token)]) -> User:
	from bmaster.database import LocalSession
	async with LocalSession() as session:
		return (await session.execute(auth_token.get_user())).scalar()

def has_permissions(*permissions: str):
	def _check(user: Annotated[User, Depends(get_user)]):
		if not user.has_permissions(*permissions):
			raise HTTPException(status.HTTP_403_FORBIDDEN, 'Not enough permissions')
	return _check

async def start():
	global config, hasher
	config = AuthConfig.model_validate(configs.main_config['auth'])
	hasher = CryptContext([config.hasher.schemas], deprecated='auto')

async def authenticate_user(username: str, password: str) -> Optional[User]:
	from bmaster.database import LocalSession
	async with LocalSession() as session, session.begin():
		user = (await session.execute(select(User).where(User.name == username))).unique().scalar_one_or_none()
		if not user: return None
		is_valid, new_hash = hasher.verify_and_update(password, user.password_hash)
		if new_hash: user.password = new_hash
	if is_valid: return user
	else: return None

@api.post("/auth/login", tags=['auth'])
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
	user = await authenticate_user(form_data.username, form_data.password)
	if not user:
		raise HTTPException(
			status.HTTP_401_UNAUTHORIZED, 'Incorrect username or password',
			headers={"WWW-Authenticate": "Bearer"},
		)
	auth_token = AuthToken(
		user_id=user.id
	)
	return Token(
		access_token=jwt_encode(auth_token.model_dump()),
		token_type='bearer'
	)


class HashRequest(BaseModel):
	text: str

@api.post('/auth/hash', dependencies=[Depends(has_permissions('bmaster.auth.hasher.hash'))], tags=['auth'])
async def hash_text(request: HashRequest):
	return hasher.hash(request.text)

@api.get('/users/me')
async def get_me(user: Annotated[User, Depends(get_user)]) -> UserInfo:
	return user.get_info()

@api.get('/users/{user_id}')
async def get_user_(user_id: int) -> UserInfo:
	from bmaster.database import LocalSession
	async with LocalSession() as session:
		user = await session.get(User, user_id)
	if not user:
		raise HTTPException(
			404, 'User not found'
		)
	return user.get_info()


class UserCreateRequest(BaseModel):
	name: str
	password: str

@api.post('/users')
async def create_user(req: UserCreateRequest) -> UserInfo:
	from bmaster.database import LocalSession
	user = User(
		name=req.name,
		password_hash=hasher.hash(req.password)
	)
	async with LocalSession() as session:
		async with session.begin():
			session.add(user)
		await session.refresh(user, ['roles'])
	return user.get_info()


class UserUpdateRequest(BaseModel):
	name: Optional[str] = None
	password: Optional[str] = None

@api.patch('/users/{user_id}')
async def update_user(user_id: int, req: UserUpdateRequest) -> UserInfo:
	from bmaster.database import LocalSession
	async with LocalSession() as session, session.begin():
		user = await session.get(User, user_id)
		if not user: raise HTTPException(status.HTTP_404_NOT_FOUND, 'User not found')
		new_name = req.name
		new_password = req.password
		if new_name: user.name = new_name
		if new_password: user.set_password(new_password)
	return user.get_info()

@api.delete('/users/{user_id}')
async def delete_user(user_id: int):
	from bmaster.database import LocalSession
	async with LocalSession() as session, session.begin():
		user = await session.get(User, user_id)
		if not user: raise HTTPException(status.HTTP_404_NOT_FOUND, 'User not found')
		await session.delete(user)
	return user.get_info()
