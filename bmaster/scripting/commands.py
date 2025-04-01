from pydantic import BaseModel, ModelWrapValidatorHandler, Field, model_validator
from typing import Coroutine, Literal, Dict, Self, Type, Any

from bmaster import icoms
from bmaster.icoms.queries import SoundQuery


# Command registry
COMMAND_REGISTRY: Dict[str, Type['ScriptCommand']] = dict()

def script_command(cls: Type['ScriptCommand']) -> Type['ScriptCommand']:
	"""Decorator to register command types"""
	type_field = cls.model_fields.get('type', None)
	if not type_field:
		raise ValueError("Command must have 'type' field")
	COMMAND_REGISTRY[type_field.default] = cls  # type: ignore
	return cls

class ScriptCommand(BaseModel):
	"""Base command model"""

	type: str = Field(..., description="Command type discriminator")

	def execute(self) -> Coroutine[Any, Any, None]:
		raise NotImplementedError()
	
	@model_validator(mode='wrap')
	@classmethod
	def validate_command_type(cls, data: Any, handler: ModelWrapValidatorHandler[Self]) -> Self:
		cmd = handler(data)
		if cls is not ScriptCommand: return cmd
		cmd_type = cmd.type
		cmd_class = COMMAND_REGISTRY.get(cmd_type, None)
		if not cmd_class:
			raise ValueError(f"Unknown command type: {cmd_type}")
		
		return cmd_class.model_validate(data)

@script_command
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

@script_command
class LogCommand(ScriptCommand):
	type: Literal['scripting.log'] = 'scripting.log'
	message: str

	async def execute(self):
		from bmaster.scripting import logger
		logger.info(f'Script info: {self.message}')

