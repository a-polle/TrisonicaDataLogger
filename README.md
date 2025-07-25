# TriSonica Mini 550p Data Logger

Cross-platform data logging software for TriSonica Mini 550p ultrasonic wind sensors across all major platforms.

## Features

- **Complete cross-platform support**: macOS, Windows, Linux, and Raspberry Pi
- **Platform-optimized tools**: Each platform has specialized features and optimizations
- **Real-time data collection**: Automatic sensor detection and data logging
- **Multiple data formats**: CSV, JSON, and tagged format support
- **Rich interfaces**: GUI on desktop platforms, headless operation for servers
- **Data quality assurance**: Built-in validation and error filtering

## Quick Start

### macOS Setup

```bash
cd mac/
chmod +x deploy.sh
./deploy.sh
./quick_start.sh
```

### Windows Setup

```cmd
cd windows\
deploy.bat
quick_start.bat
```

### Linux Setup

```bash
cd linux/
chmod +x deploy.sh
./deploy.sh
./quick_start.sh
```

### Raspberry Pi Setup

```bash
cd pi/
chmod +x deploy.sh
./deploy.sh
python3 datalogger.py
```

## Project Structure

```
TrisonicaDataLogger/
├── mac/                    # macOS-optimized version
│   ├── datalogger.py      # Rich-based GUI logger
│   ├── DataVis.py         # Data visualization
│   ├── OUTPUT/            # Generated CSV files
│   ├── PLOTS/             # Generated plots
│   ├── deploy.sh          # macOS deployment
│   ├── run_trisonica.sh   # Main launcher
│   └── quick_start.sh     # Quick launcher
├── windows/                # Windows-optimized version
│   ├── datalogger.py      # Windows GUI logger with sound alerts
│   ├── DataVis.py         # Windows file dialog integration
│   ├── deploy.bat         # Windows deployment script
│   ├── quick_start.bat    # Quick launcher
│   └── run_trisonica.bat  # Main launcher
├── linux/                  # Linux-optimized version
│   ├── datalogger.py      # Linux logger with systemd integration
│   ├── DataVis.py         # Linux file manager integration
│   ├── deploy.sh          # Linux deployment with distro detection
│   ├── quick_start.sh     # Quick launcher
│   └── run_trisonica.sh   # Main launcher
└── pi/                     # Raspberry Pi version
    ├── datalogger.py      # Headless logger
    ├── DataVis.py         # Lightweight visualization
    └── deploy.sh          # Pi deployment
```

## Usage

### Data Collection

**macOS (with UI):**
```bash
# Auto-detect sensor
./run_trisonica.sh

# Specific port
./run_trisonica.sh --port /dev/cu.usbserial-210

# Show raw data
./run_trisonica.sh --show-raw

# Custom log directory
./run_trisonica.sh --log-dir /path/to/logs
```

**Raspberry Pi (headless):**
```bash
# Auto-detect sensor
python3 datalogger.py

# Specific port
python3 datalogger.py --port /dev/ttyUSB0

# Custom log directory
python3 datalogger.py --log-dir /home/pi/data
```

### Data Visualization

```bash
# Process single file
python3 DataVis.py file.csv

# Process all CSV files in directory
python3 DataVis.py --dir /path/to/data

# Recursive search
python3 DataVis.py --dir /path/to/data --recursive

# Custom output directory
python3 DataVis.py --output /path/to/plots file.csv
```

## Supported Parameters

The logger captures and processes these TriSonica parameters:

| Parameter | Description | Unit |
|-----------|-------------|------|
| S, S2, S3 | Wind Speed (3D, 2D, Sonic) | m/s |
| D | Wind Direction | degrees |
| U, V, W | Wind Vector Components | m/s |
| T, T1, T2 | Temperature | °C |
| H | Relative Humidity | % |
| P | Atmospheric Pressure | hPa |
| PI, RO | Pitch/Roll Angles | degrees |
| MD, TD | Magnetic/True Heading | degrees |

## Dependencies

### Core Dependencies
- **Python 3.7+**
- **pyserial** - Serial communication
- **pandas** - Data processing
- **matplotlib** - Plotting
- **numpy** - Numerical operations

### Platform-Specific
- **rich** (macOS) - Terminal UI framework
- **windrose** (optional) - Wind rose plots

### Installation

Dependencies are automatically installed by the deployment scripts, or manually:

```bash
# Core dependencies
pip install pyserial pandas matplotlib numpy

# macOS additional
pip install rich

# Optional for wind roses
pip install windrose
```

## Platform Optimizations

### macOS Version
- **Rich Terminal UI**: Real-time sparklines, wind compass, statistical tables
- **High Performance**: 1000+ data points, 50Hz updates
- **Development Features**: Enhanced debugging, system monitoring
- **Large Log Files**: 50MB rotation, detailed statistics

### Raspberry Pi Version
- **Headless Operation**: No GUI dependencies, minimal resource usage
- **SD Card Friendly**: 10MB log rotation, optimized I/O
- **Low Power**: 1Hz updates, efficient data structures
- **Field Deployment**: Robust error handling, automatic recovery

## Output Files

### Data Logs
- **TrisonicaData_YYYY-MM-DD_HHMMSS.csv**: Raw sensor data with timestamps
- **TrisonicaStats_YYYY-MM-DD_HHMMSS.csv**: Statistical summaries

### Visualizations
- **Parameter plots**: Individual time-series for each sensor reading
- **Wind roses**: Directional wind speed distributions
- **Summary plots**: Multi-parameter overview charts

## Configuration

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--port` | Serial port path | auto-detect |
| `--baud` | Baud rate | 115200 |
| `--log-dir` | Output directory | ./OUTPUT |
| `--show-raw` | Display raw data | false |
| `--no-stats` | Disable statistics | false |

### Environment Variables

- `TRISONICA_PORT`: Default serial port
- `TRISONICA_LOG_DIR`: Default log directory
- `TRISONICA_BAUD_RATE`: Default baud rate

## Platform Optimizations

### macOS Version
- **Rich Terminal UI**: Real-time sparklines, wind compass, statistical tables
- **High Performance**: 1000+ data points, 50Hz updates
- **Development Features**: Enhanced debugging, system monitoring

### Windows Version
- **Sound Notifications**: Audio alerts for connection events
- **Win32 API Integration**: Native Windows system integration
- **GUI File Dialogs**: Windows-native file selection

### Linux Version
- **Desktop Notifications**: System notification integration
- **systemd Service**: Background service support
- **Distribution Detection**: Automatic package management

### Raspberry Pi Version
- **Headless Operation**: No GUI dependencies, minimal resource usage
- **SD Card Friendly**: 10MB log rotation, optimized I/O
- **Low Power**: Efficient data structures and processing

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
