import logging


logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
	handlers=[
			logging.FileHandler("data/logs.log", encoding="utf-8"),
			logging.StreamHandler()
	],
)

main_logger = logging.getLogger('bmaster')
# logger.setLevel(logging.DEBUG)
