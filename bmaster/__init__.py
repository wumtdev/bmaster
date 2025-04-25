# init
import bmaster.addons
from bmaster.logs import logger

import bmaster.configs
import bmaster.database
import bmaster.direct
import bmaster.sounds
import bmaster.icoms
import bmaster.scheduling
import bmaster.server
import bmaster.scripting
import bmaster.api
import bmaster.lite


async def start():
	# START
	logger.info("Starting config...")
	await bmaster.configs.start()
	logger.info("Config started")

	logger.info('Starting database...')
	await bmaster.database.start()
	logger.info('Database started')

	logger.info('Starting direct...')
	await bmaster.direct.start()
	logger.info('Direct started')

	logger.info('Starting sounds...')
	await bmaster.sounds.start()
	logger.info('Sounds started')

	logger.info('Starting icoms...')
	await bmaster.icoms.start()
	logger.info('Icoms started')

	logger.info("Starting scheduling...")
	await bmaster.scheduling.start()
	logger.info("Scheduling started")

	logger.info("Starting scripting...")
	await bmaster.scripting.start()
	logger.info("Scripting started")

	logger.info('Starting api..')
	await bmaster.api.start()
	logger.info('Api started')
	
	logger.info("Starting server...")
	await bmaster.server.start()
	logger.info("Server started")

	logger.info('Starting addons...')
	await bmaster.addons.start()
	logger.info('Addons started')

	logger.info('Starting lite...')
	await bmaster.lite.start()
	logger.info('Lite started')

	# POST START
	logger.info('Updating database models...')
	await bmaster.database.update_models()
	logger.info('Database models updated')

async def stop():
	logger.info("Stopping...")
	await bmaster.scheduling.stop()

	logger.info('Stopping direct...')
	await bmaster.direct.stop()
	logger.info('Direct stopped')

	logger.info("Stopped")
