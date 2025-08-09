@echo off

echo [=] Installation...

:: Create a virtual environment if it doesn't exist
if not exist venv (
    echo [-] Creating virtual environment...
    python -m venv .venv
    echo [+] Virtual environment created
)

:: Activate virtual environment
echo [-] Activating virtual environment...
call .venv/Scripts/activate
echo [+] Virtual environment activated

:: Install dependencies
echo [-] Updating pip...
python -m pip install --upgrade pip
echo [+] Updated pip

echo [-] Installing requirements...
pip install -r requirements.txt
echo [+] Installed requirements

echo [-] Creating data directory and app data...
python3 setup.py
:: There script will create the necessary directories and files and print messages

echo [=] Installation finished
