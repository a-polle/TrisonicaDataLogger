#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "Starting TriSonica Logger with auto-detection..."
python3 datalogger.py --port auto