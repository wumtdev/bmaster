from pathlib import Path
from wauxio.storage import FileSoundStorage
from wauxio.codecs.wave import from_wav
from wauxio.codecs.mp3 import from_mp3

from bmaster import logs


logger = logs.main_logger.getChild('sounds')

root = Path('data/sounds')
storage = FileSoundStorage(
	root=root,
	hide_ext=False
)


storage.use_sync_codec('.wav', from_wav)
storage.use_sync_codec('.mp3', from_mp3)


async def start():
	logger.info('Mounting sound storage...')
	# await storage.mount()
	storage.mount_sync()
	logger.info(storage.sounds)
	logger.info('Sound storage mounted')
