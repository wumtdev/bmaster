import asyncio
from fastapi import HTTPException
from pydantic import BaseModel

from bmaster import scripting
from bmaster.server import app
from bmaster.database import LocalSession
from bmaster.scripting import BaseScript, Script, ScriptData, ScriptTask, ScriptTaskOptions, ScriptTaskInfo, ScriptInfo
from bmaster.api import api


class TaskNotFound(HTTPException):
	def __init__(self, id: int):
		super().__init__(status_code=404, detail=f"Task with id '{id}' not found")

class ScriptNotFound(HTTPException):
	def __init__(self, id: int):
		super().__init__(status_code=404, detail=f"Script with id '{id}' not found")

class ScriptOptions(BaseModel):
	name: str
	script: BaseScript


@api.get('/scripting/tasks/{task_id}', tags=['scripting'])
async def get_task(task_id: int) -> ScriptTaskInfo:
	async with LocalSession() as session:
		task = await session.get(ScriptTask, task_id)
	if not task: raise TaskNotFound(task_id)
	
	return task.get_info()

@api.post('/scripting/tasks', tags=['scripting'])
async def create_task(options: ScriptTaskOptions) -> ScriptTaskInfo:
	return await scripting.create_task(options)

@api.delete('/scripting/tasks/{task_id}', tags=['scripting'])
async def delete_task(task_id: int):
	async with LocalSession() as session, session.begin():
		task = await session.get(ScriptTask, task_id)
		if not task: raise TaskNotFound()
		await session.delete(task)


@api.get('/scripting/scripts/{script_id}', tags=['scripting'])
async def get_script(script_id: int):
	async with LocalSession() as session:
		script = await session.get(Script, script_id)
	if not script: raise ScriptNotFound()

	return script.get_info()

@api.post('/scripting/scripts', tags=['scripting'])
async def create_script(options: ScriptOptions) -> ScriptInfo:
	script = Script(
		name=options.name,
		data=ScriptData(
			script=options.script
		)
	)

	async with LocalSession() as session, session.begin():
		session.add(script)
	
	return script.get_info()

@api.delete('/scripting/scripts/{script_id}', tags=['scripting'])
async def delete_script(script_id: int):
	async with LocalSession() as session, session.begin():
		script = await session.get(Script, script_id)
		if not script: raise ScriptNotFound()
		await session.delete(script)

@api.get('/scripting/scripts/execute/{script_id}', tags=['scripting'])
async def execute_script(script_id: int):
	async with LocalSession() as session, session.begin():
		script = await session.get(Script, script_id)
		if not script: raise ScriptNotFound()
		asyncio.create_task(script.execute())
