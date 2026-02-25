import asyncio
import platform
import re
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from bmaster.api.auth import require_permissions


router = APIRouter(tags=["settings"])


class VolumeSetRequest(BaseModel):
    volume: int = Field(..., ge=0, le=100)


class VolumeResponse(BaseModel):
    ok: bool
    volume: int


class UpdateResponse(BaseModel):
    ok: bool
    status: str
    backend_updated: bool = False
    frontend_updated: bool = False
    detail: str | None = None


class CheckUpdatesResponse(BaseModel):
    ok: bool
    status: str
    has_updates: bool
    backend_has_updates: bool = False
    frontend_has_updates: bool = False
    detail: str | None = None


@router.post("/reboot", dependencies=[Depends(require_permissions("bmaster.settings.reboot"))])
async def reboot() -> bool:
    system = platform.system()
    command: list[str] | None = None
    if system == "Linux":
        command = ["sh", "-c", "sleep 5 && reboot"]
    elif system == "Windows":
        command = ["shutdown", "/r", "/t", "5"]
    if command is None:
        return False

    try:
        subprocess.Popen(command)
    except Exception:
        return False
    return True

def set_system_volume(percent: int) -> bool:
    if platform.system() != "Linux":
        return False

    try:
        subprocess.run(
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return False
    return True


def get_system_volume() -> int | None:
    if platform.system() != "Linux":
        return None

    try:
        result = subprocess.run(
            ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None

    match = re.search(r"(\d+)%", result.stdout)
    return int(match.group(1)) if match else None


@router.put(
    "/volume",
    response_model=VolumeResponse,
    dependencies=[Depends(require_permissions("bmaster.settings.volume"))],
)
async def set_volume(req: VolumeSetRequest) -> VolumeResponse:
    ok = set_system_volume(req.volume)
    if not ok:
        raise HTTPException(status_code=500)
    return VolumeResponse(ok=True, volume=req.volume)


@router.get(
    "/volume",
    response_model=VolumeResponse,
    dependencies=[Depends(require_permissions("bmaster.settings.volume"))],
)
async def get_volume() -> VolumeResponse:
    res = get_system_volume()
    if res is None:
        raise HTTPException(status_code=500)
    return VolumeResponse(ok=True, volume=res)


def _run_update_sync() -> tuple[bool, bool]:
    from service import run_update

    return run_update()


def _run_check_updates_sync() -> tuple[bool, bool]:
    from service import run_check

    return run_check()


@router.post(
    "/update",
    response_model=UpdateResponse,
    dependencies=[Depends(require_permissions("bmaster.settings.updates"))],
)
async def update_endpoint() -> UpdateResponse:
    try:
        backend_updated, frontend_updated = await asyncio.to_thread(_run_update_sync)
    except Exception as exc:
        return UpdateResponse(ok=False, status="failed", detail=str(exc))

    return UpdateResponse(
        ok=True,
        status="success",
        backend_updated=backend_updated,
        frontend_updated=frontend_updated,
    )


@router.get(
    "/check_updates",
    response_model=CheckUpdatesResponse,
    dependencies=[Depends(require_permissions("bmaster.settings.updates"))],
)
async def check_updates_endpoint() -> CheckUpdatesResponse:
    try:
        backend_has_updates, frontend_has_updates = await asyncio.to_thread(
            _run_check_updates_sync
        )
    except Exception as exc:
        return CheckUpdatesResponse(
            ok=False,
            status="failed",
            has_updates=False,
            detail=str(exc),
        )

    has_updates = backend_has_updates or frontend_has_updates
    return CheckUpdatesResponse(
        ok=True,
        status="updates_available" if has_updates else "up_to_date",
        has_updates=has_updates,
        backend_has_updates=backend_has_updates,
        frontend_has_updates=frontend_has_updates,
    )
