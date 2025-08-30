import json
import yaml
from pathlib import Path
import secrets
import requests
import zipfile
import io

BASE_PATH = Path("data")
STATIC_PATH = Path("static")
DEFAULT_CONFIG_FILE = Path("defaults/config.yml")
DEFAULT_LITE_FILE = Path("defaults/lite.json")

# Data Setup
print(f"[-] Checking for directory: {BASE_PATH}...")

if not BASE_PATH.exists() or not any(BASE_PATH.iterdir()):
    BASE_PATH.mkdir(parents=True, exist_ok=True)
    print(f"[+] Directory '{BASE_PATH}' checked/created.")

    (BASE_PATH / "sounds").mkdir(parents=True, exist_ok=True)
    print(f"[+] Directory '{BASE_PATH / 'sounds'}' checked/created.")

    # config.yml
    config_path = BASE_PATH / "config.yml"
    if not config_path.exists() and DEFAULT_CONFIG_FILE.exists():
        config_data = yaml.safe_load(DEFAULT_CONFIG_FILE.read_text(encoding="utf-8"))
        if "auth" in config_data and "jwt" in config_data["auth"]:
            config_data["auth"]["jwt"]["secret_key"] = secrets.token_hex(32)

        with config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                config_data,
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
        print("[+] Config file 'config.yml' created.")

    # lite.json
    lite_config_path = BASE_PATH / "lite.json"
    if not lite_config_path.exists() and DEFAULT_LITE_FILE.exists():
        lite_config_data = json.loads(DEFAULT_LITE_FILE.read_text(encoding="utf-8"))
        with lite_config_path.open("w", encoding="utf-8") as f:
            json.dump(lite_config_data, f, ensure_ascii=False, indent=2)
        print("[+] Config file 'lite.json' created.")

    # logs.log
    logs_path = BASE_PATH / "logs.log"
    if not logs_path.exists():
        logs_path.touch()
        print("[+] Log file 'logs.log' created.")

else:
    print(f"[!] Directory '{BASE_PATH}' already exists and is not empty. Skipping...")

print("[+] Data directory and app data created")

# Static Setup 
print(f"[-] Checking for directory: {STATIC_PATH}...")
STATIC_PATH.mkdir(parents=True, exist_ok=True)
print(f"[+] Directory '{STATIC_PATH}' checked/created.")

GITHUB_RELEASE_URL = "путь до репы"

try:
    print(f"[-] Downloading frontend build from {GITHUB_RELEASE_URL}...")
    r = requests.get(GITHUB_RELEASE_URL, timeout=60)
    r.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(STATIC_PATH)

    print(f"[+] Frontend build extracted to '{STATIC_PATH}'.")

except Exception as e:
    print(f"[!] Failed to download or extract frontend: {e}")