from types import CoroutineType
from typing import Optional
from pydantic import BaseModel, Field, SerializeAsAny

from sqlalchemy import ForeignKey, Integer, Select, Text, and_, or_, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bmaster import configs, logs, database
from bmaster.database import Base, JSONModel
from bmaster.scheduling import JobTrigger, scheduler

from bmaster.scripting.commands import ScriptCommand


class ScriptingConfig(BaseModel):
	pass

config: Optional[ScriptingConfig] = None

logger = logs.logger.getChild('scripting')

async def start():
	global config
	config = ScriptingConfig.model_validate(configs.main_config['scripting'])


# --  SCRIPTS  -- #

class BaseScript(BaseModel):
	commands: list[SerializeAsAny[ScriptCommand]]

	async def execute(self) -> None:
		for cmd in self.commands:
			await cmd.execute()

class ScriptData(BaseModel):
	script: BaseScript

class ScriptInfo(BaseModel):
	id: int
	name: str
	script: BaseScript


class Script(Base):
	__tablename__ = 'scripts'

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	name: Mapped[str] = mapped_column(Text, nullable=False)
	data: Mapped[ScriptData] = mapped_column(JSONModel(ScriptData), nullable=False)

	tasks: Mapped[list["ScriptTask"]] = relationship(back_populates='script')

	def execute(self) -> CoroutineType:
		return self.data.script.execute()
	
	def get_info(self) -> ScriptInfo:
		return ScriptInfo(
			id=self.id,
			name=self.name,
			script=self.data.script
		)



# --  TASKS  -- #

class ScriptTaskInfo(BaseModel):
	id: int
	script: ScriptInfo
	tags: list[str]

class ScriptTask(Base):
	__tablename__ = 'script_tasks'

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	script_id: Mapped[int] = mapped_column(ForeignKey(Script.id), nullable=False)
	_tags: Mapped[str | None] = mapped_column("tags", Text, default="", nullable=False)

	script: Mapped[Script] = relationship(back_populates='tasks', lazy='joined')

	@property
	def tags(self) -> list[str]:
		return self._tags.split(',')
	
	@tags.setter
	def tags(self, value: list[str]):
		# cleaned_tags = [tag.strip().lower() for tag in value if tag.strip()]
		self._tags = ','.join(value)

	def search_tags(self, search_tags: list[str]) -> Select:
		# search_tags = [tag.strip().lower() for tag in search_tags if tag.strip()]
		conditions = []
		for tag in search_tags:
			# Match tags at start, middle, or end of the string
			conditions.append(
				or_(
					self._tags.ilike(f"%,{tag},%"),
					self._tags.ilike(f"{tag},%"),
					self._tags.ilike(f"%,{tag}"),
					self._tags == tag
				)
			)
		
		return select(self.__class__).where(and_(*conditions))
	
	async def delete(self):
		scheduler.remove_job(f'bmaster.scripting.scripted_task#{self.id}')
		async with database.LocalSession() as session, session.begin():
			session.delete(self)
	
	def get_info(self) -> ScriptTaskInfo:
		return ScriptTaskInfo(
			id=self.id,
			script=self.script.get_info(),
			tags=self.tags
		)

async def execute_script_task_by_id(task_id: int):
	async with database.LocalSession() as session:
		task = await session.get(ScriptTask, task_id)
	await task.script.execute()

class ScriptTaskOptions(BaseModel):
	script_id: int
	trigger: JobTrigger
	tags: list[str] = Field(default_factory=list)

async def create_task(options: ScriptTaskOptions) -> ScriptTaskInfo:
	script_id = options.script_id
	task = ScriptTask(
		script_id=script_id
	)
	task.tags = options.tags

	async with database.LocalSession() as session, session.begin():
		script = await session.get(Script, script_id)
		if not script: raise RuntimeError('Script not found')
		session.add(task)
	
	task_id = task.id
	task_info = ScriptTaskInfo(
		id=task_id,
		script=script.get_info(),
		tags=task.tags
	)

	scheduler.add_job(
		func=execute_script_task_by_id,
		id=f'bmaster.scripting.scripted_task#{task_id}',
		kwargs={
			'task_id': task_id
		},
		**options.trigger.job_kwargs()
	)

	return task_info
