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
		config_text = DEFAULT_CONFIG_FILE.read_text(encoding="utf-8")
		config_text.replace('$auth.jwt.secret_key', secrets.token_hex(32))

		with config_path.open("w", encoding="utf-8") as f:
			f.write(config_text)
		print("[+] Config file 'config.yml' created.")

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

GITHUB_RELEASE_URL = "https://github.com/wumtdev/bmaster-lite/releases/latest/download/build.zip"

try:
	print(f"[-] Downloading frontend build from {GITHUB_RELEASE_URL}...")
	r = requests.get(GITHUB_RELEASE_URL, timeout=60)
	r.raise_for_status()

	with zipfile.ZipFile(io.BytesIO(r.content)) as z:
		z.extractall(STATIC_PATH)

	print(f"[+] Frontend build extracted to '{STATIC_PATH}'.")

except Exception as e:
	print(f"[!] Failed to download or extract frontend: {e}")
