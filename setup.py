import json
from pathlib import Path
import secrets

# Default configuration data
config_data = {
    "database": {"url": "sqlite+aiosqlite:///./data/database.db"},
    "scheduling": {"url": "sqlite:///./data/database.db"},
    "scripting": {},
    "auth": {
        "jwt": {
            "secret_key": secrets.token_urlsafe(32),
            "algorithm": "HS256",
            "expire_minutes": 30,
        },
        "hasher": {"schemas": "bcrypt"},
        "service": {"enabled": True, "password": "rpass"},
    },
    "icoms": {"icoms": {"main": {"name": "Главный", "direct": True}}},
}

lite_config_data = {
    "bells": {
        "lessons": [],
        "enabled": False,
        "weekdays": {
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": False,
            "sunday": False,
        },
    },
    "announcements": {"ring_sound": None},
}

base_path = Path("data")
print(f"[-] Checking for directory: {base_path}...")

# Check if the directory exists and has no files
if not base_path.exists() or not any(base_path.iterdir()):
    try:
        base_path.mkdir(exist_ok=True)
        print(f"[+] Directory '{base_path}' checked/created.")

        sounds_path = base_path / "sounds"
        sounds_path.mkdir(exist_ok=True)
        print(f"[+] Directory '{sounds_path}' checked/created.")

        config_path = base_path / "config.json"
        if not config_path.exists():
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            print("[+] Config file 'config.json' created.")

        lite_config_path = base_path / "lite.json"
        if not lite_config_path.exists():
            with lite_config_path.open("w", encoding="utf-8") as f:
                json.dump(lite_config_data, f, ensure_ascii=False, indent=2)
            print("[+] Config file 'lite.json' created.")

        logs_path = base_path / "logs.log"
        if not logs_path.exists():
            logs_path.touch()
            print("[+] Log file 'logs.log' created.")

    except OSError as e:
        print(f"[!] Failed to setup directories: {e}")
        raise
else:
    print(f"[!] Directory '{base_path}' already exists and is not empty. Skipping...")

print("[+] Data directory and app data created")
