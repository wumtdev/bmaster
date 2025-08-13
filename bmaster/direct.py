import numpy as np
from wauxio.mixer import AudioMixer
from wauxio.output import AudioOutput
import sounddevice as sd

from bmaster import logs


logger = logs.main_logger.getChild('direct')

RATE = 48000
CHANNELS = 2
DELAY = 0.5

output_mixer: AudioMixer = AudioMixer()
output: AudioOutput = AudioOutput(
	channels=CHANNELS,
	rate=RATE
)
output.connect(output_mixer)

def out_callback(outdata, frames, time, status):
	duration = frames/RATE
	frame = output.tick(duration)

	audio = frame.audio
	if not audio: return

	data = audio.data
	outdata[:len(data)] = data

out_stream = sd.OutputStream(
	samplerate=RATE,
	blocksize=int(RATE * DELAY),
	channels=CHANNELS,
	dtype=np.float32,
	callback=out_callback
)


async def start():
	logger.info('Starting output stream...')
	out_stream.start()
	logger.info('Output stream started')

async def stop():
	logger.info('Closing output stream...')
	out_stream.close()
	logger.info('Output stream closed')
