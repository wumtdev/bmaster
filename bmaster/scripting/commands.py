from typing import Literal, Mapping, Optional, Self, Type
from pydantic import BaseModel, model_validator

from bmaster import icoms
from bmaster.icoms.queries import SoundQuery


command_map: Mapping[str, Type['ScriptCommand']] = dict()

class ScriptCommand(BaseModel):
	type: str

	async def execute(self) -> None:
		raise NotImplementedError()

	# Automatically register subclasses in the registry
	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)
		if hasattr(cls, 'type'):
			event_type = cls.model_fields['type'].default
			command_map[event_type] = cls

	# Resolve event type during validation
	@model_validator(mode='after')
	def resolve_event_type(self: Self) -> Self:
		if type(self) != ScriptCommand: return self
		model = command_map.get(self.type, None)
		if model:
			return model.model_validate(self)

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
