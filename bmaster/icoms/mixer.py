

import asyncio
from asyncio import CancelledError, Task
from typing import Optional
from wsignals import Signal


class TextMixer:
	prefix: str
	def __init__(self, prefix: str = 'missing'):
		self.prefix = prefix

	def info(self, *args, **kwargs):
		print(f"[{self.prefix}]", *args, **kwargs)

class Sound:
	duration: float
	name: str
	end: Signal
	mixer: TextMixer
	playing: Optional[Task] = None

	def __init__(self, mixer: TextMixer, duration: float, name: str):
		self.duration = duration
		self.name = name
		self.mixer = mixer
		self.end = Signal()
	
	def play(self):
		if self.playing: raise ValueError("Sound is playing")
		self.playing = asyncio.create_task(self._play_async())
	
	def stop(self):
		if not self.playing: raise ValueError("Sound is not playing")
		self.playing.cancel()
	
	async def _play_async(self):
		try:
			self.mixer.info(f"Playing sound: {self.name} ({self.duration}s)")
			await asyncio.sleep(self.duration)
			self.mixer.info(f"Finished sound: {self.name}")
			self.end.call()
		except CancelledError:
			self.mixer.info(f"Playing interrupted: {self.name}")
