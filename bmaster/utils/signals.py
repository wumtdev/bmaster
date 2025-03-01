import asyncio
from typing import Callable, Coroutine, List

type Listener = Callable[..., None | Coroutine[None, None, None]]
class Signal:
	listeners: List[Listener]

	def __init__(self):
		self.listeners = list()
	
	def connect(self, listener: Listener):
		self.listeners.append(listener)
	
	def __call__(self, listener: Listener) -> Listener:
		self.listeners.append(listener)
		return listener

	def call(self, *args, **kwargs):
		try: loop = asyncio.get_running_loop()
		except RuntimeError: loop = None
		for listener in self.listeners:
			coro = listener(*args, **kwargs)
			if asyncio.iscoroutine(coro):
				if loop:
					loop.create_task(coro)
				else:
					coro.close()
	

