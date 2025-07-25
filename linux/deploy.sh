#!/bin/bash

# TriSonica Data Logger - Linux Deployment Script
# Optimized for Linux desktop and server environments with systemd integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$SCRIPT_DIR"
LOG_DIR="$INSTALL_DIR/OUTPUT"
VENV_DIR="$INSTALL_DIR/venv"

echo -e "${BLUE}TriSonica Data Logger - Linux Deployment${NC}"
echo "=============================================="

# Function to print status
print_status() {
    echo -e "${GREEN}[OK] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

print_info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_NAME=$PRETTY_NAME
    elif command -v lsb_release >/dev/null 2>&1; then
        DISTRO=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
        DISTRO_NAME=$(lsb_release -sd)
    else
        DISTRO="unknown"
        DISTRO_NAME="Unknown Linux"
    fi
    
    print_status "Detected: $DISTRO_NAME"
}

# Check if running on Linux
check_linux() {
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        print_error "This script is designed for Linux only"
        exit 1
    fi
    print_status "Running on Linux"
}

# Check Python installation
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        echo "Install Python 3 using your package manager:"
        echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        echo "  Fedora/RHEL:   sudo dnf install python3 python3-pip"
        echo "  Arch:          sudo pacman -S python python-pip"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_status "Python $PYTHON_VERSION found"
}

# Install system dependencies based on distribution
install_system_deps() {
    print_info "Installing system dependencies..."
    
    case "$DISTRO" in
        ubuntu|debian)
            sudo apt update
            sudo apt install -y python3-dev python3-pip python3-venv build-essential \
                libfreetype6-dev libpng-dev libjpeg-dev pkg-config \
                libnotify-bin udev
            ;;
        fedora|rhel|centos)
            sudo dnf install -y python3-devel python3-pip gcc gcc-c++ \
                freetype-devel libpng-devel libjpeg-turbo-devel pkgconfig \
                libnotify systemd-udev
            ;;
        arch|manjaro)
            sudo pacman -S --needed --noconfirm python python-pip base-devel \
                freetype2 libpng libjpeg-turbo pkg-config \
                libnotify udev
            ;;
        opensuse*)
            sudo zypper install -y python3-devel python3-pip gcc gcc-c++ \
                freetype2-devel libpng16-devel libjpeg8-devel pkg-config \
                libnotify-tools systemd
            ;;
        *)
            print_warning "Unknown distribution: $DISTRO"
            print_info "Please manually install: python3-dev, build tools, and notification tools"
            ;;
    esac
    
    print_status "System dependencies installed"
}

# Setup udev rules for serial access
setup_udev_rules() {
    print_info "Setting up udev rules for serial access..."
    
    # Add user to dialout group
    if groups | grep -q dialout; then
        print_status "User already in dialout group"
    else
        sudo usermod -a -G dialout "$USER"
        print_warning "Added user to dialout group - logout/login required"
    fi
    
    # Create udev rule for TriSonica devices (if needed)
    UDEV_RULE="/etc/udev/rules.d/99-trisonica.rules"
    if [ ! -f "$UDEV_RULE" ]; then
        sudo tee "$UDEV_RULE" > /dev/null << 'EOF'
# TriSonica serial devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", ATTRS{idProduct}=="2303", MODE="0666", GROUP="dialout"
EOF
        sudo udevadm control --reload-rules
        print_status "Udev rules created"
    else
        print_status "Udev rules already exist"
    fi
}

# Create directories
create_directories() {
    print_info "Creating directories..."
    
    mkdir -p "$LOG_DIR"
    mkdir -p "$INSTALL_DIR/backups"
    mkdir -p "$INSTALL_DIR/systemd"
    
    print_status "Directories created"
}

# Create virtual environment
create_venv() {
    print_info "Creating Python virtual environment..."
    
    if [ -d "$VENV_DIR" ]; then
        print_warning "Virtual environment already exists, recreating..."
        rm -rf "$VENV_DIR"
    fi
    
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    print_status "Virtual environment created"
}

# Install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    
    source "$VENV_DIR/bin/activate"
    
    # Install required packages
    pip install pyserial rich psutil
    
    # Install optional packages for advanced features
    pip install --quiet matplotlib numpy pandas || print_warning "Optional visualization packages failed to install"
    pip install --quiet windrose || print_warning "WindRose package failed to install"
    
    # Linux-specific packages
    pip install --quiet python-daemon || print_warning "Daemon package failed to install"
    
    print_status "Dependencies installed"
}

# Create launcher scripts
create_launchers() {
    print_info "Creating launcher scripts..."
    
    # Main launcher
    cat > "$INSTALL_DIR/run_trisonica.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python3 datalogger.py "\$@"
EOF
    
    # Quick start launcher
    cat > "$INSTALL_DIR/quick_start.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
echo "Starting TriSonica Logger with auto-detection..."
python3 datalogger.py --port auto
EOF
    
    # Data visualization launcher
    cat > "$INSTALL_DIR/visualize.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
echo "Starting TriSonica Data Visualization..."
python3 DataVis.py "\$@"
EOF
    
    # Log viewer
    cat > "$INSTALL_DIR/view_logs.sh" << EOF
#!/bin/bash
LOG_DIR="$LOG_DIR"
echo "Recent TriSonica Data Files:"
echo "================================"
ls -lt "\$LOG_DIR"/*.csv 2>/dev/null | head -10
echo
echo "Latest Data Sample:"
echo "======================"
LATEST=\$(ls -t "\$LOG_DIR"/*.csv 2>/dev/null | head -1)
if [ -n "\$LATEST" ]; then
    echo "File: \$(basename "\$LATEST")"
    echo "Last 10 lines:"
    tail -10 "\$LATEST"
else
    echo "No CSV files found in OUTPUT directory"
fi
EOF
    
    # System info
    cat > "$INSTALL_DIR/system_info.sh" << EOF
#!/bin/bash
echo "Linux System Information"
echo "=================================="
echo "Distribution: \$(lsb_release -d 2>/dev/null | cut -f2 || cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"')"
echo "Kernel: \$(uname -r)"
echo "Architecture: \$(uname -m)"
echo "Hostname: \$(hostname)"
echo "User: \$(whoami)"
echo "Python: \$(python3 --version)"
echo
echo "Serial Ports:"
ls /dev/tty{USB,ACM}* 2>/dev/null || echo "No serial devices found"
echo
echo "USB Devices:"
lsusb | grep -E "(Serial|USB)" || echo "No relevant USB devices found"
echo
echo "Disk Usage (OUTPUT):"
du -sh "$LOG_DIR/" 2>/dev/null || echo "OUTPUT directory not found"
echo
echo "Process Info:"
ps aux | grep -E "(python.*datalogger|trisonica)" | grep -v grep || echo "No TriSonica processes running"
EOF

    # Service control script
    cat > "$INSTALL_DIR/service_control.sh" << EOF
#!/bin/bash
SERVICE_NAME="trisonica-logger"
SERVICE_FILE="/etc/systemd/system/\${SERVICE_NAME}.service"

case "\$1" in
    install)
        echo "Installing systemd service..."
        sudo cp systemd/trisonica-logger.service "\$SERVICE_FILE"
        sudo systemctl daemon-reload
        sudo systemctl enable "\$SERVICE_NAME"
        echo "Service installed. Use 'sudo systemctl start \$SERVICE_NAME' to start"
        ;;
    uninstall)
        echo "Uninstalling systemd service..."
        sudo systemctl stop "\$SERVICE_NAME" 2>/dev/null || true
        sudo systemctl disable "\$SERVICE_NAME" 2>/dev/null || true
        sudo rm -f "\$SERVICE_FILE"
        sudo systemctl daemon-reload
        echo "Service uninstalled"
        ;;
    status)
        systemctl status "\$SERVICE_NAME"
        ;;
    logs)
        journalctl -u "\$SERVICE_NAME" -f
        ;;
    *)
        echo "Usage: \$0 {install|uninstall|status|logs}"
        exit 1
        ;;
esac
EOF
    
    # Make scripts executable
    chmod +x "$INSTALL_DIR"/*.sh
    
    print_status "Launcher scripts created"
}

# Create systemd service file
create_systemd_service() {
    print_info "Creating systemd service file..."
    
    cat > "$INSTALL_DIR/systemd/trisonica-logger.service" << EOF
[Unit]
Description=TriSonica Data Logger
After=multi-user.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=dialout
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$VENV_DIR/bin/python datalogger.py --port auto --no-notifications
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$LOG_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    print_status "Systemd service file created"
}

# Test installation
test_installation() {
    print_info "Testing installation..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Test Python imports
    if python3 -c "import serial, rich, psutil; print('All imports successful')" 2>/dev/null; then
        print_status "Python dependencies test passed"
    else
        print_error "Python dependencies test failed"
        exit 1
    fi
    
    # Test script syntax
    if python3 -m py_compile datalogger.py; then
        print_status "Script syntax test passed"
    else
        print_error "Script syntax test failed"
        exit 1
    fi
    
    # Test notification system
    if command -v notify-send >/dev/null 2>&1; then
        print_status "Desktop notifications available"
    else
        print_warning "Desktop notifications not available"
    fi
    
    print_status "Installation test completed"
}

# Show usage information
show_usage() {
    echo
    echo -e "${GREEN}Installation complete!${NC}"
    echo
    echo "Usage:"
    echo "  Direct run:        ./run_trisonica.sh [options]"
    echo "  Quick start:       ./quick_start.sh"
    echo "  Data visualization: ./visualize.sh [file_or_dir]"
    echo "  View logs:         ./view_logs.sh"
    echo "  System info:       ./system_info.sh"
    echo "  Service control:   ./service_control.sh {install|status|logs}"
    echo
    echo "Files:"
    echo "  Application:       $INSTALL_DIR/"
    echo "  Logs:             $LOG_DIR/"
    echo "  Virtual env:      $VENV_DIR/"
    echo "  Systemd service:  $INSTALL_DIR/systemd/"
    echo
    echo "Command line options:"
    echo "  Auto-detect:       ./run_trisonica.sh"
    echo "  Specific port:     ./run_trisonica.sh --port /dev/ttyUSB0"
    echo "  Show raw data:     ./run_trisonica.sh --show-raw"
    echo "  Disable notifications: ./run_trisonica.sh --no-notifications"
    echo "  Run as daemon:     ./run_trisonica.sh --daemon"
    echo "  Custom log dir:    ./run_trisonica.sh --log-dir /var/log/trisonica"
    echo
    echo "SystemD Service:"
    echo "  Install service:   sudo ./service_control.sh install"
    echo "  Start service:     sudo systemctl start trisonica-logger"
    echo "  Check status:      ./service_control.sh status"
    echo "  View logs:         ./service_control.sh logs"
    echo
    echo -e "${PURPLE}Pro Tips:${NC}"
    echo "  - Use SIGUSR1 to print current statistics: kill -USR1 <pid>"
    echo "  - Check serial permissions: ls -l /dev/ttyUSB*"
    echo "  - Monitor with htop or systemctl status"
    echo
}

# Main installation function
main() {
    print_info "Starting Linux installation..."
    
    check_linux
    detect_distro
    check_python
    install_system_deps
    setup_udev_rules
    create_directories
    create_venv
    install_dependencies
    create_launchers
    create_systemd_service
    test_installation
    show_usage
    
    echo -e "${GREEN}Ready to start logging your TriSonica data!${NC}"
    echo
    echo "Next steps:"
    echo "1. Connect your TriSonica device via USB"
    echo "2. Run: ./quick_start.sh"
    echo "3. Or install as service: sudo ./service_control.sh install"
    echo
    read -p "Would you like to run a quick test? (y/N): " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Running quick test...${NC}"
        ./quick_start.sh --help
    fi
}

# Run main installation
main "$@"