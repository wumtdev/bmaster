import asyncio
import importlib
from pathlib import Path

from bmaster import logs


logger = logs.main_logger.getChild("plugins")

PLUGINS_DIR = Path("plugins")


async def load_plugins():
    """Load bmaster Python plugins"""
    logger.info("Loading plugins...")

    if not PLUGINS_DIR.exists():
        logger.info(f"Plugins dir '{PLUGINS_DIR}' does not exist, creating...")
        PLUGINS_DIR.mkdir()
        return

    logger.info(f"Searching plugins in '{PLUGINS_DIR}'")
    for entry in PLUGINS_DIR.iterdir():
        if entry.is_file():
            if entry.suffix != ".py":
                continue
            if entry.name == "__init__.py":
                continue
            module_path = entry
        elif entry.is_dir():
            if entry.name == "__pycache__":
                continue
            module_path = entry / "__init__.py"
            if not module_path.is_file():
                continue
        else:
            continue

        plugin_name = entry.stem
        module_name = "plugins." + plugin_name

        logger.info(f"Loading plugin '{plugin_name}', module: '{module_name}'...")
        module = importlib.import_module(module_name)

        start_fn = getattr(module, "start", None)
        if callable(start_fn):
            coro = start_fn()
            if asyncio.iscoroutine(coro):
                await coro
                logger.debug(f"Plugin '{plugin_name}' start awaited")
            else:
                logger.debug(f"Plugin '{plugin_name}' start called")
        else:
            logger.debug(f"Plugin '{plugin_name}' without start function")

        logger.info(f"Loaded plugin '{plugin_name}'")

    logger.info("Loaded plugins")
