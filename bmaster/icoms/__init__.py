from typing import Any, Mapping, Optional

from bmaster.utils import aio
from .queries import Query, QueryContext, ContextStatus
from .mixer import TextMixer


class Icom:
	name: str
	queue: list[Query] = list()
	playing: Optional[QueryContext] = None
	mixer: TextMixer
	paused: bool = False

	def __init__(self, name: str):
		self.name = name
		self.mixer = TextMixer(
			prefix="icom: "+name
		)

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


_icoms_map: Mapping[str, Icom] = {
	'main': Icom("main")
}

def get(name: str) -> Optional[Icom]:
	return _icoms_map.get(name, None)
