import anyio
import json
from typing import Optional

from bmaster import logs
from bmaster.exc import StartError


logger = logs.logger.getChild('config')

CONFIG_PATH = "data/config.json"
main_config: Optional[dict] = None

async def start():
	logger.info("Loading main config...")
	try:
		async with await anyio.open_file(CONFIG_PATH, "r", encoding="utf-8") as f:
			_data = await f.read()
			_data = json.loads(_data)
			if not isinstance(_data, dict):
				logger.critical("Invalid main config")
				raise StartError()
			global main_config
			main_config = _data
		logger.info("Main config loaded")
	except FileNotFoundError:
		logger.critical("Main config file 'data/config.json' not found")
		raise StartError()
	except json.JSONDecodeError as e:
		logger.critical("Failed to decode main config json:\n%s", e)
		raise StartError()
