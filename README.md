# TriSonica Mini 550p Data Logger

Cross-platform serial data logger and visualization utilities for the TriSonica Mini 550p ultrasonic wind sensor.

## Setup

Each directory contains platform-specific deployment scripts and runners:

### macOS
```bash
cd mac
./deploy.sh
```

### Linux
```bash
cd linux
./deploy.sh
```

### Windows
```cmd
cd windows
deploy.bat
```

### Raspberry Pi
```bash
cd pi
./deploy.sh
```

## Usage

### Serial Logging

Run from your platform folder (`mac/`, `linux/`, or `pi/`):

```bash
# Auto-detect serial port
./run_trisonica.sh

# Explicit port
./run_trisonica.sh --port /dev/ttyUSB0

# Custom log directory
./run_trisonica.sh --log-dir ./OUTPUT

# Display raw stream
./run_trisonica.sh --show-raw
```

On Raspberry Pi (headless):
```bash
python3 datalogger.py --port /dev/ttyUSB0 --log-dir /home/pi/data
```

### Visualization

```bash
# Plot single CSV file
python3 DataVis.py file.csv

# Process an entire directory
python3 DataVis.py --dir ./OUTPUT --output ./PLOTS
```

## Output Files

- `TrisonicaData_YYYY-MM-DD_HHMMSS.csv`: raw sensor readings (wind speed, direction, 3D vector components, temperature, humidity, pressure, pitch, roll, heading).
- `TrisonicaStats_YYYY-MM-DD_HHMMSS.csv`: periodic min/max/mean/std summaries.
- `PLOTS/`: generated time-series plots and wind roses.

## Dependencies

- Python 3.7+
- `pyserial`, `pandas`, `matplotlib`, `numpy`
- Optional: `rich` (terminal UI), `windrose` (directional wind speed plots)

Install manually if needed:
```bash
pip install pyserial pandas matplotlib numpy rich windrose
```

## License

MIT
