# init
from bmaster.logs import logger

import bmaster.configs
import bmaster.scheduling
import bmaster.sounds
import bmaster.icoms
import bmaster.icoms.queries
import bmaster.server
import bmaster.scripting
import bmaster.api
import bmaster.api.auth
import bmaster.api.icoms
import bmaster.api.sounds


async def start():
	logger.info("Starting config...")
	await bmaster.configs.start()
	logger.info("Config started")

	logger.info('Starting sounds...')
	await bmaster.sounds.start()
	logger.info('Sounds started')

	logger.info("Starting scheduling...")
	await bmaster.scheduling.start()
	logger.info("Scheduling started")
	
	logger.info("Starting server...")
	await bmaster.server.start()
	logger.info("Server started")

async def stop():
	logger.info("Stopping...")
	await bmaster.scheduling.stop()
	logger.info("Stopped")
