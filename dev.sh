#!/bin/bash
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt --quiet
fi

.venv/bin/python run.py --dev