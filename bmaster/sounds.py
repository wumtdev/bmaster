from pathlib import Path
import numpy as np
from wauxio.storage import FileSoundStorage
from wauxio import Audio
from wauxio.codecs.wave import from_wav
import wave

from bmaster import logs


logger = logs.logger.getChild('sounds')

root = Path('data/sounds')
storage = FileSoundStorage(
	root=root,
	hide_ext=False
)


storage.use_sync_codec('.wav', from_wav)


async def start():
	logger.info('Mounting sound storage...')
	# await storage.mount()
	storage.mount_sync()
	logger.info(storage.sounds)
	logger.info('Sound storage mounted')
