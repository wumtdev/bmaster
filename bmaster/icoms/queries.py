from typing import Any, Optional
from enum import Enum
from wauxio.mixer import AudioMixer
from wauxio import AudioReader

from bmaster import sounds
from bmaster.icoms.mixer import Sound, TextMixer
from wsignals import Signal

class ContextStatus(Enum):
	WAITING = 0
	PLAYING = 1
	STOPPED = 2
	FINISHED = 3

class QueryContext:
	mixer: AudioMixer
	query: "Query"
	finished: Signal
	stopped: Signal
	status = ContextStatus.WAITING

	def __init__(self, mixer: AudioMixer, query: "Query"):
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

	def __init__(self, name: str, priority: int = 0, force: bool = False):
		self.name = name
		self.priority = priority
		self.force = force

	def play(self, ctx: QueryContext):
		mixer = ctx.mixer

		sound = AudioReader(sounds.storage.get(self.name))
		sound.end.connect(ctx.finish)
		ctx.stopped.connect(sound.close)
		mixer.add(sound)
