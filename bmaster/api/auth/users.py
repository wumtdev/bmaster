from abc import ABC, abstractmethod
from pydantic import BaseModel


class UserInfo(BaseModel):
    type: str


class UserLocalInfo(BaseModel):
    type: str


class User(ABC):
    @abstractmethod
    def get_label(self) -> str:
        pass

    @abstractmethod
    def has_permission(self, *permissions: str) -> bool:
        pass

    @abstractmethod
    def get_info(self) -> UserInfo:
        pass

    @abstractmethod
    def get_local_info(self) -> UserLocalInfo:
        pass
