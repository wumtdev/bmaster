import asyncio
import json
import shutil
from dataclasses import dataclass
from typing import Callable, Literal, Optional

import numpy as np
from fastapi import HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field, ValidationError
from wauxio import Audio, StreamData
from wauxio.utils import AudioStack

from bmaster.api import api
from bmaster.api.auth import require_auth_token, require_bearer_jwt, require_permissions, require_user
from bmaster.api.auth.users import User
from bmaster.api.icoms.queries import query_author_from_user
from bmaster.icoms import Icom
from bmaster.icoms.queries import PlayOptions, Query, QueryStatus
import bmaster.icoms as icoms

# Frontend commonly sends chunks around 16k samples (~0.34s @48kHz).
# Keep this buffer above a single chunk to avoid regular underruns.
STREAM_STACK_SECONDS = 0.6
DEFAULT_STREAM_RATE = 48_000


class StartMessageValidationError(Exception):
	def __init__(self, error: str, validation_errors: Optional[list[dict]] = None):
		super().__init__(error)
		self.error = error
		self.validation_errors = validation_errors or []


class APIStreamStartRequest(BaseModel):
	type: Literal['start']
	icom: str
	priority: int = 0
	force: bool = False
	codec: str
	container: str
	mime_type: str
	timeslice_ms: Optional[int] = Field(default=None, gt=0)
	sample_rate_hint: Optional[int] = Field(default=None, gt=0)
	channels_hint: Optional[int] = Field(default=None, gt=0)


@dataclass(frozen=True)
class NormalizedStreamStart:
	icom: str
	priority: int
	force: bool
	rate: int
	channels: int
	container: str


class APIStreamQuery(Query):
	type = 'api.stream'
	priority: int
	force: bool
	stack: AudioStack

	def __init__(self, icom: Icom, priority: int, force: bool, rate: int, channels: int, author: Optional[User] = None):
		self.description = 'Playing plain audio stream'
		self.priority = priority
		self.force = force
		self.author = query_author_from_user(author) if author else None

		self.stack = AudioStack(
			rate=rate,
			channels=channels,
			samples=max(1, int(rate * STREAM_STACK_SECONDS))
		)

		super().__init__(icom)

	def play(self, options: PlayOptions):
		super().play(options)
		mixer = options.mixer
		mixer.add(self.stack.pull)

	def stop(self):
		super().stop()


class FFmpegStreamDecoder:
	def __init__(self, process: asyncio.subprocess.Process, rate: int, channels: int, on_audio: Callable[[Audio], None]):
		self.process = process
		self.rate = rate
		self.channels = channels
		self._on_audio = on_audio
		self._buffer = bytearray()
		self._stderr = ''
		self._read_error: Optional[BaseException] = None
		self._stdout_task: Optional[asyncio.Task] = None
		self._stderr_task: Optional[asyncio.Task] = None
		self._closed = False

	@classmethod
	async def create(cls, container: str, rate: int, channels: int, on_audio: Callable[[Audio], None]) -> 'FFmpegStreamDecoder':
		command = [
			'ffmpeg',
			'-hide_banner',
			'-loglevel',
			'error',
			'-fflags',
			'+discardcorrupt',
			'-f',
			container,
			'-i',
			'pipe:0',
			'-vn',
			'-ac',
			str(channels),
			'-ar',
			str(rate),
			'-f',
			'f32le',
			'pipe:1',
		]
		process = await asyncio.create_subprocess_exec(
			*command,
			stdin=asyncio.subprocess.PIPE,
			stdout=asyncio.subprocess.PIPE,
			stderr=asyncio.subprocess.PIPE,
		)
		decoder = cls(process, rate, channels, on_audio)
		decoder._stdout_task = asyncio.create_task(decoder._read_stdout())
		decoder._stderr_task = asyncio.create_task(decoder._read_stderr())
		return decoder

	def _consume_buffer(self):
		frame_bytes = self.channels * np.dtype(np.float32).itemsize
		aligned = len(self._buffer) - (len(self._buffer) % frame_bytes)
		if aligned <= 0:
			return

		pcm = bytes(self._buffer[:aligned])
		del self._buffer[:aligned]

		arr = np.frombuffer(pcm, dtype=np.float32)
		if arr.size == 0:
			return
		arr = arr.reshape((-1, self.channels))
		self._on_audio(Audio(arr.copy(), self.rate))

	async def _read_stdout(self):
		try:
			assert self.process.stdout is not None
			while True:
				chunk = await self.process.stdout.read(8192)
				if not chunk:
					break
				self._buffer.extend(chunk)
				self._consume_buffer()
		except BaseException as e:
			self._read_error = e

	async def _read_stderr(self):
		try:
			assert self.process.stderr is not None
			stderr_bytes = await self.process.stderr.read()
			self._stderr = stderr_bytes.decode(errors='replace').strip()
		except BaseException:
			self._stderr = ''

	def _raise_if_broken(self):
		if self._read_error:
			raise RuntimeError(f'ffmpeg decoder failed: {self._read_error}')

		returncode = self.process.returncode
		if returncode not in (None, 0):
			detail = self._stderr or f'exit code {returncode}'
			raise RuntimeError(f'ffmpeg decoder exited: {detail}')

	async def push_bytes(self, data: bytes):
		if not data:
			return
		self._raise_if_broken()
		assert self.process.stdin is not None
		try:
			self.process.stdin.write(data)
			await self.process.stdin.drain()
		except (BrokenPipeError, ConnectionResetError) as e:
			raise RuntimeError('ffmpeg decoder pipe closed') from e
		self._raise_if_broken()

	async def close(self):
		if self._closed:
			return
		self._closed = True

		if self.process.stdin is not None and not self.process.stdin.is_closing():
			self.process.stdin.close()

		try:
			await asyncio.wait_for(self.process.wait(), timeout=1.0)
		except asyncio.TimeoutError:
			self.process.terminate()
			try:
				await asyncio.wait_for(self.process.wait(), timeout=1.0)
			except asyncio.TimeoutError:
				self.process.kill()
				await self.process.wait()

		await asyncio.gather(
			*(task for task in (self._stdout_task, self._stderr_task) if task is not None),
			return_exceptions=True,
		)
		self._consume_buffer()
		self._buffer.clear()


def _is_supported_opus_format(codec: str, container: str, mime_type: str) -> bool:
	codec = codec.strip().lower()
	container = container.strip().lower()
	mime_type = mime_type.strip().lower()
	return codec == 'opus' and container == 'webm' and 'audio/webm' in mime_type


def _parse_start_message(raw_text: str) -> NormalizedStreamStart:
	try:
		start = APIStreamStartRequest.model_validate_json(raw_text)
	except ValidationError as e:
		raise StartMessageValidationError(
			'validation error',
			validation_errors=e.errors(),
		) from e

	if not _is_supported_opus_format(start.codec, start.container, start.mime_type):
		raise StartMessageValidationError(
			'unsupported stream format: supported only audio/webm+opus'
		)

	return NormalizedStreamStart(
		icom=start.icom,
		priority=start.priority,
		force=start.force,
		rate=start.sample_rate_hint or DEFAULT_STREAM_RATE,
		channels=start.channels_hint or 1,
		container=start.container.strip().lower(),
	)


def _is_stop_message(raw_text: str) -> bool:
	try:
		data = json.loads(raw_text)
	except json.JSONDecodeError:
		return False
	return isinstance(data, dict) and data.get('type') == 'stop'


def _get_ws_bearer_token(ws: WebSocket) -> Optional[str]:
	auth_header = ws.headers.get('authorization')
	if auth_header:
		scheme, _, token = auth_header.partition(' ')
		if scheme.lower() == 'bearer' and token:
			return token
		if scheme and not token:
			# Allow raw token in header for non-standard clients.
			return scheme
	return ws.query_params.get('token')


async def _require_stream_user(ws: WebSocket) -> Optional[User]:
	token = _get_ws_bearer_token(ws)
	if not token:
		await ws.send_json({
			'type': 'error',
			'error': 'missing bearer token',
		})
		await ws.close(code=status.WS_1008_POLICY_VIOLATION)
		return None

	try:
		jwt_data = require_bearer_jwt(token)
		auth_token = require_auth_token(jwt_data)
		user = await require_user(auth_token)
		require_permissions('bmaster.icoms.queries.stream')(user)
		return user
	except HTTPException as e:
		await ws.send_json({
			'type': 'error',
			'error': e.detail,
		})
		await ws.close(code=status.WS_1008_POLICY_VIOLATION)
		return None


async def _send_validation_error(ws: WebSocket, error: StartMessageValidationError):
	payload = {
		'type': 'error',
		'error': error.error,
	}
	if error.validation_errors:
		payload['validation.errors'] = error.validation_errors
	await ws.send_json(payload)


@api.websocket('/queries/stream')
async def play_stream(ws: WebSocket):
	await ws.accept()

	try:
		user = await _require_stream_user(ws)
	except WebSocketDisconnect:
		return
	if not user:
		return

	start: Optional[NormalizedStreamStart] = None
	q: Optional[APIStreamQuery] = None
	decoder: Optional[FFmpegStreamDecoder] = None

	try:
		try:
			first_message = await ws.receive()
		except WebSocketDisconnect:
			return

		if first_message.get('type') == 'websocket.disconnect':
			return

		start_text = first_message.get('text')
		if start_text is None:
			await ws.send_json({
				'type': 'error',
				'error': 'first websocket message must be a JSON start payload',
			})
			await ws.close()
			return

		try:
			start = _parse_start_message(start_text)
		except StartMessageValidationError as e:
			await _send_validation_error(ws, e)
			await ws.close()
			return

		icom = icoms.get(start.icom)
		if not icom:
			await ws.send_json({
				'type': 'error',
				'error': 'icom not found',
			})
			await ws.close()
			return

		channels = start.channels
		# TODO: Implement multi-channel support.
		if channels != 1:
			await ws.send_json({
				'type': 'error',
				'error': 'only 1 channel supported',
			})
			await ws.close()
			return

		rate = start.rate

		if not shutil.which('ffmpeg'):
			await ws.send_json({
				'type': 'error',
				'error': 'ffmpeg is required for opus stream decoding but is not installed',
			})
			await ws.close()
			return

		q = APIStreamQuery(
			icom=icom,
			priority=start.priority,
			force=start.force,
			rate=rate,
			channels=channels,
			author=user,
		)

		try:
			await ws.send_json({
				'type': 'waiting' if q.status == QueryStatus.WAITING else 'started',
				'query': q.get_info().model_dump(mode='json'),
			})
		except WebSocketDisconnect:
			q.cancel()
			return

		@q.on_cancel
		async def on_cancel():
			try:
				await ws.send_json({
					'type': 'cancelled',
					'query': q.get_info().model_dump(mode='json'),
				})
				await ws.close()
			except WebSocketDisconnect:
				pass
			except RuntimeError:
				pass

		@q.on_stop
		async def on_stop():
			try:
				await ws.send_json({
					'type': 'stopped',
					'query': q.get_info().model_dump(mode='json'),
				})
			except WebSocketDisconnect:
				pass
			except RuntimeError:
				pass

		@q.on_play
		async def on_play():
			try:
				await ws.send_json({
					'type': 'started',
					'query': q.get_info().model_dump(mode='json'),
				})
			except WebSocketDisconnect:
				pass

		def _push_audio(audio: Audio):
			assert q is not None
			q.stack.push(StreamData(audio))

		decoder = await FFmpegStreamDecoder.create(
			container=start.container,
			rate=rate,
			channels=channels,
			on_audio=_push_audio,
		)

		while True:
			try:
				message = await ws.receive()
			except WebSocketDisconnect:
				break

			message_type = message.get('type')
			if message_type == 'websocket.disconnect':
				break
			if message_type != 'websocket.receive':
				continue

			binary_data = message.get('bytes')
			if binary_data is not None:
				try:
					assert decoder is not None
					await decoder.push_bytes(binary_data)
				except Exception as e:
					await ws.send_json({
						'type': 'error',
						'error': f'audio decode failed: {e}',
					})
					await ws.close()
					break
				continue

			text_data = message.get('text')
			if text_data is not None:
				if _is_stop_message(text_data):
					break
				await ws.send_json({
					'type': 'error',
					'error': 'invalid control message, expected {"type":"stop"}',
				})
				await ws.close()
				break
	finally:
		if decoder is not None:
			try:
				await decoder.close()
			except Exception:
				pass

		if q and q.status in (QueryStatus.WAITING, QueryStatus.PLAYING):
			q.cancel()
