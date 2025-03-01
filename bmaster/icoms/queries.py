from typing import Any, Optional
from enum import Enum

from bmaster.icoms.mixer import Sound, TextMixer
from bmaster.utils.signals import Signal

class ContextStatus(Enum):
	WAITING = 0
	PLAYING = 1
	STOPPED = 2
	FINISHED = 3

class QueryContext:
	mixer: TextMixer
	query: "Query"
	finished: Signal
	stopped: Signal
	status = ContextStatus.WAITING

	def __init__(self, mixer: Any, query: "Query"):
		self.mixer = mixer
		self.query = query
		
		self.finished = Signal()
		self.stopped = Signal()

	def finish(self):
		self.status = ContextStatus.FINISHED
		self.finished.call()

	def stop(self):
		self.status = ContextStatus.STOPPED
		self.stopped.call()

# abstract/virtual
class Query:
	duration: Optional[float] = None
	priority: int = 0
	force: bool = False

	def play(self, ctx: QueryContext):
		pass

class SoundQuery(Query):
	name: str
	priority: int
	force: bool
	duration: int

	def __init__(self, name: str, priority: int = 0, force: bool = False, duration: float = 3.0):
		self.name = name
		self.priority = priority
		self.force = force
		self.duration = duration

	def play(self, ctx: QueryContext):
		mixer = ctx.mixer
		sound = Sound(mixer, self.duration, self.name)

		@sound.end
		def on_sound_end():
			ctx.finish()
		
		ctx.stopped.connect(sound.stop)
		
		sound.play()
