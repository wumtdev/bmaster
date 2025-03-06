from dataclasses import dataclass
from typing import Coroutine, Mapping, Optional, TYPE_CHECKING
from enum import Enum
import uuid
from wauxio.mixer import AudioMixer
from wauxio import AudioReader

from bmaster import sounds


if TYPE_CHECKING:
	from bmaster.icoms import Icom


class QueryStatus(Enum):
	WAITING = 0
	PLAYING = 1
	FINISHED = 2
	CANCELLED = 3

@dataclass(frozen=True)
class PlayOptions:
	mixer: AudioMixer

# abstract/virtual
class Query:
	id: uuid.UUID
	icom: "Icom"
	duration: Optional[float] = None
	priority: int = 0
	force: bool = False
	status: QueryStatus = QueryStatus.WAITING

	def __init__(self, icom: "Icom"):
		self.icom = icom
		query_id = uuid.uuid4()
		self.id = query_id
		_queries_map[query_id] = self
		icom._add_query(self)

	def cancel(self):
		icom = self.icom
		status = self.status
		match status:
			case QueryStatus.WAITING:
				self.icom._remove_query(self)
			case QueryStatus.PLAYING:
				self.stop()
				icom._on_playing_finished()
			case _:
				raise RuntimeError(f'Could not cancel query with status {status}')
		self.status = QueryStatus.CANCELLED

	def play(self, options: PlayOptions) -> None | Coroutine:
		self.status = QueryStatus.PLAYING
	
	def stop(self):
		if self.status != QueryStatus.PLAYING:
			raise RuntimeError('Query is not playing')
		del _queries_map[self.id]
		self.status = QueryStatus.WAITING
	
	def finish(self):
		self.status = QueryStatus.FINISHED
		del _queries_map[self.id]
		self.icom._on_playing_finished()

class SoundQuery(Query):
	name: str
	priority: int
	force: bool
	sound: Optional[AudioReader] = None

	def __init__(self, icom: "Icom", name: str, priority: int = 0, force: bool = False):
		self.name = name
		self.priority = priority
		self.force = force
		super().__init__(icom)

	def play(self, options: PlayOptions):
		super().play(options)
		mixer = options.mixer

		sound = AudioReader(sounds.storage.get(self.name))
		self.sound = sound
		sound.end.connect(self.finish)
		mixer.add(sound)
	
	def stop(self):
		self.sound.close()
		self.sound = None
		super().stop()


_queries_map: Mapping[uuid.UUID, Query] = dict()

def get_by_id(id: uuid.UUID) -> Optional[Query]:
	return _queries_map.get(id, None)
