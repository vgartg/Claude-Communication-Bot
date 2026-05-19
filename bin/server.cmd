@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv" (
  python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -e .

if "%CCB_PORT%"=="" set CCB_PORT=3000
python -m claude_comm_bot.main
