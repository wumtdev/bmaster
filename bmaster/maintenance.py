import argparse
import io
import json
import secrets
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from cert_setup import setup_cert


REPO_PATH = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_PATH / "data"
STATIC_PATH = REPO_PATH / "static"
DEFAULT_CONFIG_PATH = REPO_PATH / "defaults" / "config.yml"
SSL_KEY_PATH = DATA_PATH / "key.pem"
SSL_CERT_PATH = DATA_PATH / "cert.pem"
CONFIG_PATH = DATA_PATH / "config.yml"
SOUNDS_PATH = DATA_PATH / "sounds"
LOGS_PATH = DATA_PATH / "logs.log"
FRONTEND_META_FILE = STATIC_PATH / ".frontend_release.json"
FRONTEND_INDEX_FILE = STATIC_PATH / "index.html"

GITHUB_RELEASE_ZIP_URL = "https://github.com/wumtdev/bmaster-lite/releases/latest/download/build.zip"
GITHUB_LATEST_API = "https://api.github.com/repos/wumtdev/bmaster-lite/releases/latest"
SYSTEMD_SERVICE_NAME = "bmaster.service"


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    id: int
    published_at: str


def _read_installed_release(meta_file: Path = FRONTEND_META_FILE) -> Optional[ReleaseInfo]:
    if not meta_file.exists():
        return None
    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        return ReleaseInfo(
            tag_name=str(data.get("tag_name", "")),
            id=int(data.get("id", 0)),
            published_at=str(data.get("published_at", "")),
        )
    except Exception:
        return None


def _write_installed_release(info: ReleaseInfo, meta_file: Path = FRONTEND_META_FILE) -> None:
    meta_file.write_text(
        json.dumps(
            {
                "tag_name": info.tag_name,
                "id": info.id,
                "published_at": info.published_at,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _fetch_latest_release(session: requests.Session) -> ReleaseInfo:
    response = session.get(
        GITHUB_LATEST_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "bmaster-maintenance",
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    tag_name = data.get("tag_name")
    release_id = data.get("id")
    published_at = data.get("published_at")
    if not tag_name or not release_id or not published_at:
        raise RuntimeError("Invalid GitHub release response")

    return ReleaseInfo(
        tag_name=str(tag_name),
        id=int(release_id),
        published_at=str(published_at),
    )


def _download_zip(session: requests.Session) -> bytes:
    response = session.get(
        GITHUB_RELEASE_ZIP_URL,
        headers={"User-Agent": "bmaster-maintenance"},
        timeout=60,
    )
    response.raise_for_status()
    return response.content


def _replace_static_files(static_path: Path, zip_bytes: bytes, meta_file_name: str) -> None:
    tmp_dir = Path(tempfile.mkdtemp(prefix="frontend_build_"))
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            archive.extractall(tmp_dir)

        entries = list(tmp_dir.iterdir())
        build_root = entries[0] if len(entries) == 1 and entries[0].is_dir() else tmp_dir

        for item in static_path.iterdir():
            if item.name == meta_file_name:
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        for item in build_root.iterdir():
            destination = static_path / item.name
            if item.is_dir():
                shutil.copytree(item, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(item, destination)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _sync_frontend(static_path: Path = STATIC_PATH, force: bool = False) -> bool:
    static_path.mkdir(parents=True, exist_ok=True)
    meta_file = static_path / FRONTEND_META_FILE.name
    index_file = static_path / FRONTEND_INDEX_FILE.name
    installed = _read_installed_release(meta_file)

    with requests.Session() as session:
        latest = _fetch_latest_release(session)
        should_download = (
            force
            or installed is None
            or installed.id < latest.id
            or not index_file.exists()
        )
        if not should_download:
            return False

        zip_bytes = _download_zip(session)

    _replace_static_files(static_path, zip_bytes, meta_file.name)
    _write_installed_release(latest, meta_file)
    return True


def _git(repo_path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def update_backend(repo_path: Path = REPO_PATH) -> bool:
    before = _git(repo_path, "rev-parse", "HEAD")
    subprocess.run(["git", "pull"], cwd=repo_path, check=True)
    after = _git(repo_path, "rev-parse", "HEAD")
    return before != after


def check_backend_updates(repo_path: Path = REPO_PATH) -> bool:
    _git(repo_path, "fetch")
    try:
        counts = _git(repo_path, "rev-list", "--left-right", "--count", "HEAD...@{u}")
    except subprocess.CalledProcessError:
        return False
    ahead, behind = [int(value) for value in counts.split()]
    return behind > 0


def check_frontend_updates(static_path: Path = STATIC_PATH) -> bool:
    installed = _read_installed_release(static_path / FRONTEND_META_FILE.name)
    if installed is None:
        return True

    with requests.Session() as session:
        latest = _fetch_latest_release(session)
    return latest.id > installed.id


def bootstrap(update_cert: bool = False) -> int:
    print(f"[-] Checking for directory: {DATA_PATH}...")
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    print(f"[+] Directory '{DATA_PATH}' checked/created.")

    SOUNDS_PATH.mkdir(parents=True, exist_ok=True)
    print(f"[+] Directory '{SOUNDS_PATH}' checked/created.")

    if not CONFIG_PATH.exists() and DEFAULT_CONFIG_PATH.exists():
        config_text = DEFAULT_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "$auth.jwt.secret_key",
            secrets.token_hex(32),
        )
        CONFIG_PATH.write_text(config_text, encoding="utf-8")
        print("[+] Config file 'config.yml' created.")

    if not LOGS_PATH.exists():
        LOGS_PATH.touch()
        print("[+] Log file 'logs.log' created.")

    if update_cert:
        print("[-] Updating self-signed certificate...")
    else:
        print("[-] Generating self-signed certificate...")

    cert_generated = setup_cert(
        SSL_KEY_PATH,
        SSL_CERT_PATH,
        regenerate=update_cert,
    )
    if cert_generated and update_cert:
        print("[+] Certificate updated")
    elif cert_generated:
        print("[+] Generated self-signed certificate")
    print("[+] Data directory and app data created")

    print(f"[-] Checking for directory: {STATIC_PATH}...")
    STATIC_PATH.mkdir(parents=True, exist_ok=True)
    print(f"[+] Directory '{STATIC_PATH}' checked/created.")

    print(f"[-] Fetching frontend release metadata from {GITHUB_LATEST_API}...")
    try:
        frontend_updated = _sync_frontend(STATIC_PATH, force=False)
    except Exception as exc:
        print(f"[!] Failed to download or extract frontend: {exc}")
    else:
        if frontend_updated:
            print(f"[+] Frontend build extracted to '{STATIC_PATH}'.")
            print(f"[+] Frontend release metadata saved to '{FRONTEND_META_FILE}'.")
        else:
            print("[+] Frontend is already up to date.")

    if update_cert and cert_generated:
        print("[!] Certificate has been updated. Download it again and add it to trusted on all clients.")

    return 0


def run_update() -> tuple[bool, bool]:
    backend_updated = update_backend(REPO_PATH)
    frontend_updated = _sync_frontend(STATIC_PATH, force=False)
    return backend_updated, frontend_updated


def run_check() -> tuple[bool, bool]:
    backend_has_updates = check_backend_updates(REPO_PATH)
    frontend_has_updates = check_frontend_updates(STATIC_PATH)
    return backend_has_updates, frontend_has_updates


def _handle_bootstrap(args: argparse.Namespace) -> int:
    return bootstrap(update_cert=args.update_cert)


def _handle_check(_: argparse.Namespace) -> int:
    backend_has_updates, frontend_has_updates = run_check()
    if backend_has_updates:
        print("Backend: update available")
    if frontend_has_updates:
        print("Frontend: update available")
    if not backend_has_updates and not frontend_has_updates:
        print("Updates: none")
    return 0


def _handle_update(_: argparse.Namespace) -> int:
    backend_updated, frontend_updated = run_update()
    print("Backend: updated" if backend_updated else "Backend: no updates")
    print("Frontend: updated" if frontend_updated else "Frontend: no updates")
    if backend_updated:
        print(f"[!] Restart service to apply backend changes: sudo systemctl restart {SYSTEMD_SERVICE_NAME}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="bmaster install/update maintenance utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subparsers.add_parser("bootstrap", help="Initialize data, cert and frontend")
    bootstrap_parser.add_argument(
        "--update-cert",
        action="store_true",
        help="Force regenerate SSL certificate even if it already exists",
    )
    bootstrap_parser.set_defaults(handler=_handle_bootstrap)

    check_parser = subparsers.add_parser("check", help="Check backend and frontend updates")
    check_parser.set_defaults(handler=_handle_check)

    update_parser = subparsers.add_parser("update", help="Update backend and frontend")
    update_parser.set_defaults(handler=_handle_update)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Maintenance failed: {exc}")
        raise SystemExit(1)
