from pathlib import Path
from wauxio.storage import FileSoundStorage

from bmaster import logs


logger = logs.logger.getChild('sounds')

root = Path()
storage = FileSoundStorage(
	root=root,
	hide_ext=False
)

async def start():
	logger.info('Mounting sound storage...')
	await storage.mount()
	logger.info('Sound storage mounted')
