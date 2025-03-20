from typing import Optional
from pydantic import BaseModel

from sqlalchemy import JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from bmaster import configs, logs
from bmaster.database import Base, LocalSession
from bmaster.scheduling import JobTrigger, scheduler

from bmaster.scripting.commands import ScriptCommand


class ScriptingConfig(BaseModel):
	pass

config: Optional[ScriptingConfig] = None

logger = logs.logger.getChild('scripting')

async def start():
	global config
	config = ScriptingConfig.model_validate(configs.main_config['scripting'])


class BaseScript(BaseModel):
	commands: list[ScriptCommand]

	async def execute(self):
		for cmd in self.commands:
			cmd.execute()

class ScriptedTaskData(BaseModel):
	script: BaseScript

class ScriptedTask(Base):
	__tablename__ = 'scripted_tasks'

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	data: Mapped[ScriptedTaskData] = mapped_column(JSON, nullable=False)

async def execute_scripted_task_by_id(task_id: int):
	async with LocalSession() as session:
		task = await session.get(ScriptedTask, task_id)
		await task.data.script.execute()


class TaskOptions(BaseModel):
	script: BaseScript
	trigger: JobTrigger

async def create_task(options: TaskOptions) -> ScriptedTask:
	task = ScriptedTask(
		data=ScriptedTaskData(
			script=options.script
		)
	)

	async with LocalSession() as session:
		async with session.begin():
			session.add(task)
	task_id = task.id

	scheduler.add_job(
		func=execute_scripted_task_by_id,
		id=f'bmaster.scripting.scripted_task#{task_id}',
		kwargs={
			'task_id': task_id
		},
		**options.trigger.job_kwargs()
	)
