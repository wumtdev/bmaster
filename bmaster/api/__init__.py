from fastapi import APIRouter

from bmaster.server import app
from bmaster.logs import main_logger


logger = main_logger.getChild('api')

api = APIRouter()


async def start():
	logger.info('Importing endpoints...')

	import bmaster.api.auth
	await bmaster.api.auth.start()

	import bmaster.api.icoms
	import bmaster.api.icoms.listen
	import bmaster.api.icoms.queries
	import bmaster.api.icoms.queries.audio
	import bmaster.api.icoms.queries.sound
	import bmaster.api.icoms.queries.stream

	from bmaster.api import scripting
	from bmaster.api import sounds

	logger.info('Including routers...')

	api.include_router(sounds.router, prefix='/sounds')
	app.include_router(api, prefix='/api')

	logger.info('Started')
