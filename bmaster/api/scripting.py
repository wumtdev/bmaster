import asyncio
from fastapi import HTTPException
from pydantic import BaseModel

from bmaster import scripting
from bmaster.server import app
from bmaster.database import LocalSession
from bmaster.scripting import BaseScript, Script, ScriptData, ScriptTask, ScriptTaskOptions, ScriptTaskInfo, ScriptInfo


class TaskNotFound(HTTPException):
	def __init__(self, id: int):
		super().__init__(status_code=404, detail=f"Task with id '{id}' not found")

class ScriptNotFound(HTTPException):
	def __init__(self, id: int):
		super().__init__(status_code=404, detail=f"Script with id '{id}' not found")

class ScriptOptions(BaseModel):
	name: str
	script: BaseScript


@app.get('/scripting/tasks/{task_id}')
async def get_task(task_id: int) -> ScriptTaskInfo:
	async with LocalSession() as session:
		task = await session.get(ScriptTask, task_id)
	if not task: raise TaskNotFound(task_id)
	
	return task.get_info()

@app.post('/scripting/tasks')
async def create_task(options: ScriptTaskOptions) -> ScriptTaskInfo:
	return await scripting.create_task(options)

@app.delete('/scripting/tasks/{task_id}')
async def delete_task(task_id: int):
	async with LocalSession() as session:
		async with session.begin():
			task = await session.get(ScriptTask, task_id)
			if not task: raise TaskNotFound()
			await session.delete(task)


@app.get('/scripting/scripts/{script_id}')
async def get_script(script_id: int):
	async with LocalSession() as session:
		script = await session.get(Script, script_id)
	if not script: raise ScriptNotFound()

	return script.get_info()

@app.post('/scripting/scripts')
async def create_script(options: ScriptOptions) -> ScriptInfo:
	script = Script(
		name=options.name,
		data=ScriptData(
			script=options.script
		)
	)

	async with LocalSession() as session:
		async with session.begin():
			session.add(script)
	
	return script.get_info()

@app.delete('/scripting/scripts/{script_id}')
async def delete_script(script_id: int):
	async with LocalSession() as session:
		async with session.begin():
			script = await session.get(Script, script_id)
			if not script: raise ScriptNotFound()
			await session.delete(script)

@app.get('/scripting/scripts/execute/{script_id}')
async def execute_script(script_id: int):
	async with LocalSession() as session:
		async with session.begin():
			script = await session.get(Script, script_id)
			if not script: raise ScriptNotFound()
			asyncio.create_task(script.execute())
