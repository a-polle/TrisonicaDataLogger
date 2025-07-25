#!/bin/bash
cd "/Users/apollo/Documents/Master/Thesis/PrepProject/4.0/TriSonica/mac"
source venv/bin/activate
echo "Starting Trisonica Logger with auto-detection..."
python3 datalogger.py --port auto
