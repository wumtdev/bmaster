from fastapi.responses import FileResponse
from bmaster.api import api
from bmaster.logs import main_logger
import bmaster.server

logger = main_logger.getChild('certs')

@api.get('/certs/cert.cer')
async def download_cert():
    return FileResponse(
        path=bmaster.server.config.ssl.cert_path
    )
