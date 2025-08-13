import asyncio
import sys
import signal
from typing import Optional

import bmaster


# def cancel_loop(loop):
# 	tasks = asyncio.all_tasks(loop)
# 	for task in tasks: task.cancel()
# 	loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
# 	loop.close()

main_task: Optional[asyncio.Task] = None
async def main():
	global main_task

	loop = asyncio.get_running_loop()
	main_task = asyncio.current_task(loop)
	# if sys.platform != "win32":
	# 	for sig in (signal.SIGINT, signal.SIGTERM):
	# 		loop.add_signal_handler(sig, lambda *_: main_task.cancel())

	await bmaster.start()

	try: await loop.create_future()
	except asyncio.CancelledError: pass

	await bmaster.stop()

if __name__ == "__main__":
	asyncio.run(main())


# def stop_loop(loop: AbstractEventLoop):
# 	tasks = asyncio.all_tasks(loop)
# 	for task in tasks: task.cancel()
# 	# Ensure all tasks are completed before closing the loop
# 	loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
# 	loop.close()

# if __name__ == "__main__":
# 	loop = asyncio.new_event_loop()
# 	asyncio.set_event_loop(loop)

# 	if sys.platform != "win32":
# 		for sig in (signal.SIGINT, signal.SIGTERM):
# 			loop.add_signal_handler(sig, lambda *_: stop_signal.set())
	
# 	loop.create_task(start())
# 	try: loop.run_forever()
# 	except KeyboardInterrupt: print("interrupted")
# 	finally:
# 		# Cancel all running tasks
# 		tasks = asyncio.all_tasks(loop)
# 		for task in tasks: task.cancel()
# 		# Ensure all tasks are completed before closing the loop
# 		loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
# 		loop.close()
