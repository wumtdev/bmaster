from fastapi import HTTPException

from bmaster import scripting
from bmaster.server import app
from bmaster.database import LocalSession
from bmaster.scripting import ScriptedTask, TaskOptions


class TaskNotFound(HTTPException):
	def __init__(self, id: int):
		super().__init__(status_code=404, detail=f"Task with name '{id}' not found")

# @app.get('/scripting/tasks/{task_id}')
# async def get_task(task_id: int):
# 	async with LocalSession() as session:
# 		task = await session.get(ScriptedTask, task_id)
	
# 	if not task: raise TaskNotFound(task_id)
	
# 	return task



# @app.post('/scripting/tasks')
# async def create_task(options: TaskOptions) -> ScriptedTask:
# 	return scripting.create_task(options)
