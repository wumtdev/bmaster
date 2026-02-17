from pathlib import Path
from cert_setup import setup_cert
import argparse
import secrets
import json
import requests
import zipfile
import io

DATA_PATH = Path("data")
STATIC_PATH = Path("static")
DEFAULT_CONFIG_PATH = Path("defaults/config.yml")
SSL_KEY_PATH = DATA_PATH / 'key.pem'
SSL_CERT_PATH = DATA_PATH / 'cert.pem'
CONFIG_PATH = DATA_PATH / 'config.yml'
SOUNDS_PATH = DATA_PATH / 'sounds'
LOGS_PATH = DATA_PATH / 'logs.log'
FRONTEND_META_PATH = STATIC_PATH / '.frontend_release.json'

parser = argparse.ArgumentParser()
parser.add_argument(
	"--update-cert",
	action="store_true",
	help="Force regenerate SSL certificate even if it already exists",
)
args, _ = parser.parse_known_args()

# Data Setup
print(f"[-] Checking for directory: {DATA_PATH}...")

DATA_PATH.mkdir(parents=True, exist_ok=True)
print(f"[+] Directory '{DATA_PATH}' checked/created.")

SOUNDS_PATH.mkdir(parents=True, exist_ok=True)
print(f"[+] Directory '{SOUNDS_PATH}' checked/created.")

# config.yml
if not CONFIG_PATH.exists() and DEFAULT_CONFIG_PATH.exists():
	config_text = DEFAULT_CONFIG_PATH.read_text(encoding="utf-8") \
		.replace('$auth.jwt.secret_key', secrets.token_hex(32))

	with CONFIG_PATH.open("w", encoding="utf-8") as f:
		f.write(config_text)
	print("[+] Config file 'config.yml' created.")

# logs.log
if not LOGS_PATH.exists():
	LOGS_PATH.touch()
	print("[+] Log file 'logs.log' created.")


if args.update_cert:
	print('[-] Updating self-signed certificate...')
else:
	print('[-] Generating self-signed certificate...')

cert_generated = setup_cert(
	SSL_KEY_PATH,
	SSL_CERT_PATH,
	regenerate=args.update_cert,
)
if cert_generated and args.update_cert:
	print('[+] Certificate updated')
elif cert_generated:
	print('[+] Generated self-signed certificate')

print("[+] Data directory and app data created")


# Static Setup 
print(f"[-] Checking for directory: {STATIC_PATH}...")
STATIC_PATH.mkdir(parents=True, exist_ok=True)
print(f"[+] Directory '{STATIC_PATH}' checked/created.")

GITHUB_RELEASE_URL = "https://github.com/wumtdev/bmaster-lite/releases/latest/download/build.zip"
GITHUB_LATEST_API = "https://api.github.com/repos/wumtdev/bmaster-lite/releases/latest"

try:
	print(f"[-] Fetching frontend release metadata from {GITHUB_LATEST_API}...")
	release_response = requests.get(
		GITHUB_LATEST_API,
		headers={
			"Accept": "application/vnd.github+json",
			"User-Agent": "bmaster-setup",
		},
		timeout=10,
	)
	release_response.raise_for_status()
	release_data = release_response.json()
	release_info = {
		"tag_name": str(release_data.get("tag_name", "")),
		"id": int(release_data.get("id", 0)),
		"published_at": str(release_data.get("published_at", "")),
	}
	if not release_info["tag_name"] or not release_info["id"] or not release_info["published_at"]:
		raise RuntimeError("Invalid GitHub release response")

	print(f"[-] Downloading frontend build from {GITHUB_RELEASE_URL}...")
	build_response = requests.get(
		GITHUB_RELEASE_URL,
		headers={"User-Agent": "bmaster-setup"},
		timeout=60,
	)
	build_response.raise_for_status()

	with zipfile.ZipFile(io.BytesIO(build_response.content)) as z:
		z.extractall(STATIC_PATH)

	FRONTEND_META_PATH.write_text(
		json.dumps(release_info, ensure_ascii=False, indent=2),
		encoding="utf-8",
	)

	print(f"[+] Frontend build extracted to '{STATIC_PATH}'.")
	print(f"[+] Frontend release metadata saved to '{FRONTEND_META_PATH}'.")

except Exception as e:
	print(f"[!] Failed to download or extract frontend: {e}")

if args.update_cert and cert_generated:
	print("[!] Certificate has been updated. Download it again and add it to trusted on all clients.")
