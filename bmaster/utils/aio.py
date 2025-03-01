import asyncio
from typing import Coroutine


class AIONoLoop(Exception):
	"""Exception raised when no running event loop is found."""
	pass


def run(body: Coroutine | None, ignore: bool = False):
	if asyncio.iscoroutine(body):
		try: loop = asyncio.get_running_loop()
		except RuntimeError: loop = None
		if loop: loop.create_task(body)
		else:
			body.close()
			if not ignore: raise AIONoLoop()
