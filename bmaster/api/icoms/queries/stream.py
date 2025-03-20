from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import numpy as np
from pydantic import BaseModel, ValidationError
from wauxio import AudioReader, Audio, StreamData
from wauxio.utils import AudioStack

from bmaster.server import app
import bmaster.icoms as icoms
from bmaster.icoms import Icom
from bmaster.icoms.queries import PlayOptions, Query, QueryStatus


class APIStreamRequest(BaseModel):
	icom: str
	priority: int = 0
	force: bool = False
	rate: int
	channels: int

class APIStreamQuery(Query):
	name = 'api.stream'
	priority: int
	force: bool
	stack: AudioStack

	def __init__(self, icom: Icom, priority: int, force: bool, rate: int, channels: int):
		self.description = "Playing plain audio stream"
		self.priority = priority
		self.force = force

		self.stack = AudioStack(
			rate=rate,
			channels=channels,
			samples=int(rate*2)
		)

		super().__init__(icom)

	def play(self, options: PlayOptions):
		super().play(options)
		mixer = options.mixer
		mixer.add(self.stack.pull)
	
	def stop(self):
		super().stop()

@app.websocket('/queries/stream')
async def play_stream(ws: WebSocket):
	await ws.accept()
	
	try:
		try:
			request = APIStreamRequest.model_validate_json(await ws.receive_text())
		except ValidationError as e:
			await ws.send_json({
				'type': 'error',
				'error': 'validation error',
				'validation.errors': e.errors()
			})
			await ws.close()
			return

		icom = icoms.get(request.icom)
		if not icom:
			await ws.send_json({
				'type': 'error',
				'error': 'icom not found'
			})
			await ws.close()

		channels = request.channels
		# TODO: Implement multi-channels
		if channels != 1:
			await ws.send_json({
				'type': 'error',
				'error': 'only 1 channel supported'
			})
			await ws.close()
		
		rate = request.rate
	except WebSocketDisconnect: return

	q = APIStreamQuery(
		icom=icom,
		priority=request.priority,
		force=request.force,
		rate=rate,
		channels=channels
	)
	
	try:
		await ws.send_json({
			'type': 'waiting' if q.status == QueryStatus.WAITING else 'started',
			'query': q.get_info().model_dump_json()
		})
	except WebSocketDisconnect:
		q.cancel()
		return
	
	async def on_cancel():
		try:
			await ws.send_json({
				'type': 'cancelled',
				'query': q.get_info().model_dump_json()
			})
			await ws.close()
		except WebSocketDisconnect: pass
		except RuntimeError: pass
	
	async def on_stop():
		try:
			await ws.send_json({
				'type': 'stopped',
				'query': q.get_info().model_dump_json()
			})
		except WebSocketDisconnect: pass
		except RuntimeError: pass
	
	async def on_play():
		try:
			await ws.send_json({
				'type': 'started',
				'query': q.get_info().model_dump_json()
			})
		except WebSocketDisconnect: pass

	q.on_cancel.connect_async(on_cancel)
	q.on_stop.connect_async(on_stop)
	q.on_play.connect_async(on_play)

	async for msg in ws.iter_bytes():
		arr = np.frombuffer(msg, dtype=np.float32).reshape((-1, channels))
		# TODO: Implement multi-channel support
		audio = Audio(arr, rate)
		q.stack.push(StreamData(audio))
	
	if q.status in (QueryStatus.WAITING, QueryStatus.PLAYING):
		q.cancel()
