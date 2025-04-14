from pydantic import BaseModel, ModelWrapValidatorHandler, Field, ValidationError, model_validator
from typing import Coroutine, Literal, Dict, Self, Type, Any

from bmaster import icoms
from bmaster.icoms.queries import SoundQuery


command_registry: dict[str, Type['ScriptCommand']] = dict()
class ScriptCommand(BaseModel):
	type: str = Field(..., description="Command type discriminator")

	def execute(self) -> Coroutine[Any, Any, None]:
		raise NotImplementedError()
	
	@model_validator(mode='wrap')
	@classmethod
	def validate_type(cls, data: Any, handler: ModelWrapValidatorHandler[Self]) -> Self:
		ent = handler(data)
		if cls is not ScriptCommand: return ent
		ent_type = ent.type
		ent_class = command_registry.get(ent_type, None)
		if not ent_class: raise ValidationError(f'Unknown entity type: {ent_type}')
		return ent_class.model_validate(data)
	
	@staticmethod
	def register(cls: Type[Self]) -> Type[Self]:
		type_field = cls.model_fields.get('type', None)
		if not type_field: raise ValueError('Missing type field')
		command_registry[type_field.default] = cls  # type: ignore
		return cls

@ScriptCommand.register
class PlaySoundCommand(ScriptCommand):
	type: Literal['queries.sound'] = 'queries.sound'
	sound_name: str
	icom: str
	priority: int
	force: bool

	async def execute(self):
		icom = icoms.get(self.icom)
		if not icom: return
		SoundQuery(
			icom=icom,
			sound_name=self.sound_name,
			priority=self.priority,
			force=self.force
		)

@ScriptCommand.register
class LogCommand(ScriptCommand):
	type: Literal['scripting.log'] = 'scripting.log'
	message: str

	async def execute(self):
		from bmaster.scripting import logger
		logger.info(f'Script info: {self.message}')

