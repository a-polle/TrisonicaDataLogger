#!/bin/bash

# TriSonica Data Logger - Raspberry Pi Deployment Script
# Optimized for Raspberry Pi 3 B+ and similar ARM-based systems

echo "TriSonica Data Logger - Raspberry Pi Setup"
echo "=============================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    print_warning "This script is optimized for Raspberry Pi. Continuing anyway..."
fi

# Update system packages
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip if not already installed
print_status "Installing Python 3 and development tools..."
sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential

# Install system dependencies for matplotlib and other packages
print_status "Installing system dependencies..."
sudo apt install -y libfreetype6-dev libpng-dev libjpeg-dev libopenblas-dev libhdf5-dev pkg-config

# Create virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
print_status "Installing Python packages..."
pip install pyserial rich pandas matplotlib numpy

# Optional: Install windrose for wind rose plots
print_status "Installing windrose (optional)..."
pip install windrose || print_warning "Failed to install windrose - wind rose plots will be skipped"

# Create necessary directories
print_status "Creating directory structure..."
mkdir -p OUTPUT
mkdir -p PLOTS
mkdir -p logs

# Create launcher scripts
print_status "Creating launcher scripts..."

# Quick start script
cat > quick_start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 datalogger.py --port auto
EOF

# Generic run script
cat > run_trisonica.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 datalogger.py "$@"
EOF

# Log viewer script
cat > view_logs.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

echo "Recent TriSonica Data Files:"
echo "================================"
ls -lt OUTPUT/*.csv 2>/dev/null | head -5

echo
echo "Latest Data Sample:"
echo "======================"
LATEST=$(ls -t OUTPUT/*.csv 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
    echo "File: $(basename "$LATEST")"
    echo "Last 10 lines:"
    tail -10 "$LATEST"
else
    echo "No CSV files found in OUTPUT directory"
fi
EOF

# System info script
cat > system_info.sh << 'EOF'
#!/bin/bash
echo "Raspberry Pi System Information"
echo "=================================="
echo "OS: $(lsb_release -d 2>/dev/null | cut -f2 || uname -s)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo "CPU: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)"
echo "Memory: $(free -h | grep '^Mem:' | awk '{print $2}')"
echo "Python: $(python3 --version)"
echo
echo "USB Devices:"
lsusb | grep -E "(Serial|USB)" || echo "No relevant USB devices found"
echo
echo "Serial Ports:"
ls /dev/tty{USB,ACM}* 2>/dev/null || echo "No serial devices found"
echo
echo "Disk Usage (OUTPUT):"
du -sh OUTPUT/ 2>/dev/null || echo "OUTPUT directory not found"
EOF

# Make scripts executable
chmod +x *.sh

print_status "Setup completed successfully!"
echo
echo "Quick Start Guide:"
echo "====================="
echo "1. Connect your TriSonica device via USB"
echo "2. Run: ./quick_start.sh"
echo "3. Or run: ./run_trisonica.sh --port /dev/ttyUSB0"
echo "4. View logs: ./view_logs.sh"
echo "5. Generate plots: python3 DataVis.py OUTPUT/"
echo
echo "Directory Structure:"
echo "  OUTPUT/     - CSV data files"
echo "  PLOTS/      - Generated plot images"  
echo "  logs/       - System logs"
echo "  venv/       - Python virtual environment"
echo
print_status "TriSonica Data Logger is ready for Raspberry Pi!"

# Test the installation
print_status "Testing installation..."
source venv/bin/activate
python3 -c "import serial, pandas, matplotlib, rich; print('All core dependencies installed successfully')" || print_error "Some dependencies failed to install"