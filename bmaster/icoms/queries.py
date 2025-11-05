from asyncio import create_task
import asyncio
from dataclasses import dataclass
from typing import Coroutine, Mapping, Optional, TYPE_CHECKING
from enum import Enum
import uuid
from pydantic import BaseModel
from wauxio.mixer import AudioMixer
from wauxio import Audio, AudioReader, AudioReaderType, StreamOptions, StreamData
from wsignals import Signal
import playsound3

from bmaster import sounds


if TYPE_CHECKING:
	from bmaster.icoms import Icom
	from bmaster.api.auth.users import UserInfo


class QueryStatus(Enum):
	WAITING = 'waiting'
	PLAYING = 'playing'
	FINISHED = 'finished'
	CANCELLED = 'cancelled'

@dataclass(frozen=True)
class PlayOptions:
	mixer: AudioMixer

class QueryAuthor(BaseModel):
	type: Optional[str] = None
	name: str
	label: Optional[str] = None

	# @staticmethod
	# def from_user(user: UserInfo):
	# 	match user.type:
	# 		case 'account':
	# 			return QueryAuthor(
	# 				type='account',
	# 				name=user.name,
	# 				label=f'#{user.id}'
	# 			)
	# 		case 'root':
	# 			return QueryAuthor(
	# 				type='root',
	# 				name='Администратор'
	# 			)
	# 	return QueryAuthor(
	# 		type='uknown',
	# 		label='Неизвестный'
	# 	)

class QueryInfo(BaseModel):
	id: uuid.UUID
	type: Optional[str]
	description: Optional[str]
	icom: str
	priority: int
	force: bool
	duration: Optional[float]
	status: QueryStatus
	author: Optional[QueryAuthor] = None

# abstract/virtual
class Query:
	id: uuid.UUID
	type: Optional[str] = None
	description: Optional[str] = None
	icom: "Icom"
	duration: Optional[float] = None
	priority: int = 0
	force: bool = False
	status: QueryStatus = QueryStatus.WAITING
	author: Optional[QueryAuthor] = None

	on_play: Signal
	on_stop: Signal
	on_finish: Signal
	on_cancel: Signal

	def __init__(self, icom: "Icom"):
		self.on_play = Signal()
		self.on_stop = Signal()
		self.on_finish = Signal()
		self.on_cancel = Signal()

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
		del _queries_map[self.id]
		self.on_cancel.call()

	def play(self, options: PlayOptions) -> None | Coroutine:
		self.status = QueryStatus.PLAYING
		self.on_play.call()
	
	def stop(self):
		if self.status != QueryStatus.PLAYING:
			raise RuntimeError('Query is not playing')
		self.status = QueryStatus.WAITING
		self.on_stop.call()
	
	def finish(self):
		self.status = QueryStatus.FINISHED
		del _queries_map[self.id]
		self.icom._on_playing_finished()
		self.on_finish.call()
	
	def get_info(self) -> QueryInfo:
		return QueryInfo(
			id=self.id,
			type=self.type,
			description=self.description,
			icom=self.icom.id,
			priority=self.priority,
			force=self.force,
			duration=self.duration,
			status=self.status,
			author=self.author
		)


class SoundQueryInfo(QueryInfo):
	sound_name: str

class SoundQuery(Query):
	type = 'sounds.sound'
	sound_name: str
	priority: int
	force: bool
	# player: Optional[AudioReader] = None
	p: Optional[playsound3.playsound3.Sound] = None

	def __init__(self, icom: "Icom", sound_name: str, priority: int = 0, force: bool = False, author: Optional[QueryAuthor] = None):
		self.description = f"Playing sound: '{sound_name}'"
		self.sound_name = sound_name
		self.priority = priority
		self.force = force
		self.author = author
		super().__init__(icom)

	def play(self, options: PlayOptions):
		super().play(options)
		# mixer = options.mixer

		# audio = sounds.storage.get(self.sound_name)
		# if not audio:
		# 	self.finish()
		# 	return
		#
		# player = AudioReader(audio)
		# self.player = player
		# player.end.connect(self.finish)
		# mixer.add(player)
		self.p = playsound3.playsound(f'data/sounds/{self.sound_name}', block=False)
		loop = asyncio.get_running_loop()
		loop.run_in_executor(None, self.wait)

	def wait(self):
		p = self.p
		try: p.wait()
		except: pass
		if p is self.p:
			self.finish()
	
	def stop(self):
		self.p.stop()
		self.p = None
		super().stop()
	
	def get_info(self):
		data = super().get_info()
		return SoundQueryInfo(
			**data.model_dump(),
			sound_name=self.sound_name
		)

class AudioQuery(Query):
	type = 'audio'
	audio: Audio
	priority: int
	force: bool
	player: Optional[AudioReader] = None

	def __init__(self, icom: "Icom", audio: Audio, priority: int = 0, force: bool = False, author: Optional[QueryAuthor] = None):
		self.description = "Playing plain audio"
		self.audio = audio
		self.priority = priority
		self.force = force
		self.author = author
		super().__init__(icom)

	def play(self, options: PlayOptions):
		super().play(options)
		mixer = options.mixer

		player = AudioReader(self.audio)
		self.player = player
		player.end.connect(self.finish)
		mixer.add(player)
	
	def stop(self):
		self.player.close()
		self.player = None
		super().stop()

class StreamQuery(Query):
	type = 'stream'
	stream: AudioReaderType
	priority: int
	force: bool

	def __init__(self, icom: "Icom", stream: AudioReaderType, priority: int = 0, force: bool = False, author: Optional[QueryAuthor] = None):
		self.description = "Playing plain audio stream"
		self.stream = stream
		self.priority = priority
		self.force = force
		self.author = author
		super().__init__(icom)
	
	def _read(self, options: StreamOptions) -> StreamData:
		frame = self.stream(options)
		if frame.last: self.finish()
		return frame

	def play(self, options: PlayOptions):
		super().play(options)
		mixer = options.mixer
		mixer.add(self._read)
	
	def stop(self):
		self.player.close()
		self.player = None
		super().stop()

_queries_map: Mapping[uuid.UUID, Query] = dict()

def get_by_id(id: uuid.UUID) -> Optional[Query]:
	return _queries_map.get(id, None)
