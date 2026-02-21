#!/bin/bash
set -euo pipefail

echo "[=] Installation..."

# ---------- helpers ----------
need_root_for_apt() {
  if command -v apt-get >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

apt_install() {
  local pkgs=("$@")
  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    sudo apt-get update
    sudo apt-get install -y "${pkgs[@]}"
  else
    apt-get update
    apt-get install -y "${pkgs[@]}"
  fi
}

# ---------- ensure OS deps (Debian-like) ----------
if need_root_for_apt; then
  echo "[-] Ensuring base packages (curl, ca-certificates)..."
  apt_install curl ca-certificates
  echo "[+] Base packages are installed"
else
  echo "[!] apt-get not found. This script expects Debian/Ubuntu-like systems."
  exit 1
fi

# ---------- ensure python + pip ----------
echo "[-] Checking if Python 3 is installed..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "[!] Python3 not found. Installing..."
  apt_install python3
fi
echo "[+] Python 3 is installed"

echo "[-] Checking if pip is installed..."
if ! command -v pip3 >/dev/null 2>&1; then
  echo "[!] pip not found. Installing python3-pip..."
  apt_install python3-pip
fi
echo "[+] pip is installed"

# (Optional) venv module is often useful even if you use uv
echo "[-] Ensuring python3-venv..."
apt_install python3-venv
echo "[+] python3-venv is installed"

# ---------- install uv (official script) ----------
echo "[-] Installing uv via official script..."
curl -LsSf https://astral.sh/uv/install.sh | sh
echo "[+] uv installed"

# ---------- resolve uv path ----------
UV_BIN="/usr/bin/uv"
if [ ! -x "$UV_BIN" ]; then
  # Fallback: common install location if PATH isn't updated yet
  if [ -x "$HOME/.local/bin/uv" ]; then
    UV_BIN="$HOME/.local/bin/uv"
  else
    echo "[!] uv not found at /usr/bin/uv or ~/.local/bin/uv"
    echo "    Try re-opening your shell or add uv to PATH, then re-run."
    exit 1
  fi
fi

echo "[+] Using uv at: $UV_BIN"

# ---------- create venv if missing ----------
if [ ! -d ".venv" ]; then
  echo "[-] Creating virtual environment (.venv)..."
  "$UV_BIN" venv .venv
  echo "[+] Virtual environment created"
fi

# ---------- install dependencies ----------
echo "[-] Installing dependencies (uv sync)..."
"$UV_BIN" sync
echo "[+] Installed requirements"

# ---------- setup ----------
echo "[-] Creating data directory and app data..."
"$UV_BIN" run --no-sync setup.py
echo "[+] Setup completed"

echo "[=] Installation finished"
echo "---------------------------------------------------------"
echo "INFO: Project uses uv. Prefer uv instead of pip for dependency management."
echo "INFO: Docs: https://docs.astral.sh/uv/getting-started/"
echo "INFO: Run the app: $UV_BIN run --no-sync main.py"