import asyncio
import importlib
from pathlib import Path

from bmaster import logs


logger = logs.logger.getChild('addons')

ADDONS_DIR = Path('./addons')

async def mount_addons():
	if not ADDONS_DIR.exists():
		ADDONS_DIR.mkdir()
		return
	
	for entry in ADDONS_DIR.iterdir():
		if entry.is_file():
			if entry.suffix != '.py': continue
			if entry.name == '__init__.py': continue
			module_path = entry
		elif entry.is_dir():
			if entry.name == '__pycache__': continue
			module_path = entry / '__init__.py'
			if not module_path.is_file(): continue
		else:
			continue

		addon_name = entry.stem
		module_name = 'addons.' + addon_name
		
		logger.info(f'Mounting addon \'{addon_name}\', module: \'{module_name}\'...')

		module = importlib.import_module(module_name)
		start_fn = getattr(module, 'start', None)
		if start_fn:
			coro = start_fn()
			if asyncio.iscoroutine(coro):
				await coro
		
		logger.info(f'Addon \'{addon_name}\' mounted')

async def start():
	logger.info('Mounting addons...')
	await mount_addons()
	logger.info('Addons mounted')
