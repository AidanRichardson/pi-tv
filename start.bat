@echo off

:: Check if the .venv directory does not exist
if not exist ".venv\" (
    python -m venv .venv
    call .venv\Scripts\pip install -r requirements.txt
)

:: Run the python script
.venv\Scripts\python run.py --port 8000