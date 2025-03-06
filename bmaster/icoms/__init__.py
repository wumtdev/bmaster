import asyncio
from typing import Mapping, Optional
from pydantic import BaseModel
from wauxio.output import AudioOutput
from wauxio.mixer import AudioMixer
from wauxio.utils import AudioStack

from bmaster import direct, logs
from bmaster.utils import aio
from .queries import PlayOptions, Query, QueryInfo


logger = logs.logger.getChild('icoms')


class IcomInfo(BaseModel):
	name: str
	playing: Optional[QueryInfo]
	queue: list[QueryInfo]
	paused: bool


class Icom:
	name: str
	queue: list[Query] = list()
	playing: Optional[Query] = None
	mixer: AudioMixer
	paused: bool = False
	output: AudioOutput

	def __init__(self, name: str):
		self.name = name
		mixer = AudioMixer()
		output = AudioOutput(
			rate=48000,
			channels=2
		)
		output.connect(mixer.mix)
		self.mixer = mixer
		self.output = output
	
	def run(self):
		return self.output.run(0.5)

	def start(self):
		if not self.paused: ValueError("Icom is not paused")
		self.paused = False
		next_query = self._take_next_query()
		if next_query: self._play_query(next_query)

	def stop(self):
		if self.paused: ValueError("Icom is paused")
		self.paused = True

		playing = self.playing
		if playing:
			playing.stop()
			self.playing = None
			self._add_query(playing)

	def _add_query(self, query: Query):
		if not self.paused:
			# directly play new query without queue if icom is free
			if not self.playing:
				self._play_query(query)
				return
			
			# check if new query can interrupt playing queries (is force)
			if query.force:
				playing = self.playing
				# check if new query has a higher priority than playing query
				if query.force > playing.force or query.priority > playing.priority:
					# stop playing query and play new query instead
					playing.stop()
					self.playing = None
					self._play_query(query)
					self._add_query(playing)
					return
		
		# insert a new request into the queue by sorting priority
		for i, playing in enumerate(self.queue):
			if query.force > playing.force or query.priority > playing.priority:
				self.queue.insert(i, query)
				break
		else:
			self.queue.append(query)
	
	def _remove_query(self, query: Query):
		self.queue.remove(query)
	
	def _take_next_query(self) -> Optional[Query]:
		queue = self.queue
		if len(queue) == 0: return None
		query = queue[0]
		del queue[0]
		return query

	def _play_query(self, query: Query):
		if self.playing: raise RuntimeError("There's already playing query")
		options = PlayOptions(
			mixer=self.mixer
		)
		self.playing = query
		aio.run(query.play(options))

	def _on_playing_finished(self):
		self.playing = None
		query = self._take_next_query()
		if query: self._play_query(query)
	
	def get_info(self) -> IcomInfo:
		playing = self.playing
		return IcomInfo(
			name=self.name,
			playing=playing.get_info() if self.playing else None,
			queue=list(map(Query.get_info, self.queue)),
			paused=self.paused
		)


_icoms_map: Mapping[str, Icom] = dict()

def get(name: str) -> Optional[Icom]:
	return _icoms_map.get(name, None)

async def start():
	logger.info('Starting main icom...')
	main_icom = Icom('main')
	_icoms_map['main'] = main_icom
	asyncio.create_task(main_icom.run())


	rate = main_icom.output.rate
	channels = main_icom.output.channels
	stack = AudioStack(
		rate=rate,
		channels=channels,
		samples=int(rate * direct.DELAY * 2)
	)
	main_icom.output.listen(stack.push)
	direct.output_mixer.add(stack.pull)

	logger.info('Main icom started')
