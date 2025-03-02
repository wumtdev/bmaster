import asyncio
from typing import Any, Mapping, Optional
from wauxio.output import AudioOutput
from wauxio.mixer import AudioMixer
from wauxio.utils import AudioStack

from bmaster import direct, logs
from bmaster.utils import aio
from .queries import Query, QueryContext, ContextStatus
from .mixer import TextMixer


logger = logs.logger.getChild('icoms')

class Icom:
	name: str
	queue: list[Query] = list()
	playing: Optional[QueryContext] = None
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
		if self.playing:
			playing.stop()
			self.playing = None
			self.add_query(playing.query)

	def add_query(self, query: Query):
		if not self.paused:
			# directly play new query without queue if icom is free
			if not self.playing:
				self._play_query(query)
				return
			
			# check if new query can interrupt playing queries (is force)
			if query.force:
				playing = self.playing
				q = playing.query
				# check if new query has a higher priority than playing query
				if query.force > q.force or query.priority > q.priority:
					# stop playing query and play new query instead
					playing.stop()
					self.playing = None
					self._play_query(query)
					self.add_query(q)
					return
		
		# insert a new request into the queue by sorting priority
		for i, q in enumerate(self.queue):
			if query.force > q.force or query.priority > q.priority:
				self.queue.insert(i, query)
				break
		else:
			self.queue.append(query)
	
	def cancel_query(self, query: Query):
		playing = self.playing
		if playing and playing.query == query:
			playing.stop()
			self._on_playing_finished()
			return
		self.queue.remove(query)
	
	def _take_next_query(self) -> Optional[Query]:
		queue = self.queue
		if len(queue) == 0: return None
		query = queue[0]
		del queue[0]
		return query

	def _play_query(self, query: Query):
		if self.playing: raise RuntimeError("There's already playing context")

		ctx = QueryContext(
			mixer=self.mixer,
			query=query
		)

		# attach finish handler to proccess next query
		ctx.finished.connect(self._on_playing_finished)

		self.playing = ctx
		aio.run(query.play(ctx))

	def _on_playing_finished(self):
		self.playing = None
		query = self._take_next_query()
		if query: self._play_query(query)


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
