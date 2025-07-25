#!/bin/bash

# Trisonica Data Logger - macOS Deployment Script (Fixed)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Keep everything in mac directory
MAC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$MAC_DIR"
LOG_DIR="$MAC_DIR/logs"
VENV_DIR="$INSTALL_DIR/venv"

echo -e "${BLUE}Trisonica Data Logger - macOS Deployment${NC}"
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

# Check if running on macOS
check_macos() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_error "This script is designed for macOS only"
        exit 1
    fi
    print_status "Running on macOS"
}

# Check Python installation
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        echo "Please install Python 3 from https://www.python.org/ or use Homebrew:"
        echo "brew install python"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_status "Python $PYTHON_VERSION found"
}

# Check for Homebrew (optional)
check_homebrew() {
    if command -v brew &> /dev/null; then
        print_status "Homebrew detected"
        echo "Would you like to install additional tools via Homebrew? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            brew install --quiet watch htop || print_warning "Failed to install optional tools"
        fi
    else
        print_warning "Homebrew not found (optional)"
    fi
}

# Create directories
create_directories() {
    echo -e "${BLUE}Creating directories...${NC}"
    
    mkdir -p "$LOG_DIR"
    mkdir -p "$INSTALL_DIR/backups"
    
    print_status "Directories created"
}

# Create virtual environment
create_venv() {
    echo -e "${BLUE}Creating Python virtual environment...${NC}"
    
    if [ -d "$VENV_DIR" ]; then
        print_warning "Virtual environment already exists, recreating..."
        rm -rf "$VENV_DIR"
    fi
    
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_status "Virtual environment created"
}

# Install Python dependencies
install_dependencies() {
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    
    source "$VENV_DIR/bin/activate"
    
    # Install required packages
    pip install pyserial rich psutil
    
    # Optional packages for advanced features
    pip install --quiet matplotlib numpy pandas || print_warning "Optional packages failed to install"
    
    print_status "Dependencies installed"
}

# Copy application files
copy_files() {
    echo -e "${BLUE}Copying application files...${NC}"
    
    # Files are already in the mac directory, no need to copy
    chmod +x "$INSTALL_DIR/datalogger.py"
    
    print_status "Files prepared"
}

# Create launcher scripts
create_launchers() {
    echo -e "${BLUE}Creating launcher scripts...${NC}"
    
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
echo "Starting Trisonica Logger with auto-detection..."
python3 datalogger.py --port auto
EOF
    
    # Log viewer
    cat > "$INSTALL_DIR/view_logs.sh" << EOF
#!/bin/bash
LOG_DIR="$LOG_DIR"
echo "Recent log files:"
ls -la "\$LOG_DIR"/*.csv 2>/dev/null | tail -10
echo
echo "Latest data (last 20 lines):"
tail -20 "\$LOG_DIR"/TrisonicaData_*.csv 2>/dev/null | head -20
EOF
    
    # System info
    cat > "$INSTALL_DIR/system_info.sh" << EOF
#!/bin/bash
echo "System Information:"
echo "OS: \$(sw_vers -productName) \$(sw_vers -productVersion)"
echo "Hardware: \$(system_profiler SPHardwareDataType | grep "Model Name" | cut -d: -f2 | xargs)"
echo "Memory: \$(system_profiler SPHardwareDataType | grep "Memory:" | cut -d: -f2 | xargs)"
echo "Python: \$(python3 --version)"
echo
echo "Disk Usage:"
df -h "$LOG_DIR" 2>/dev/null || echo "Log directory not found"
echo
echo "USB Devices:"
system_profiler SPUSBDataType | grep -E "(Product ID|Vendor ID|Serial Number)" | head -10
EOF
    
    # Make scripts executable
    chmod +x "$INSTALL_DIR"/*.sh
    
    print_status "Launcher scripts created"
}

# Test installation
test_installation() {
    echo -e "${BLUE}Testing installation...${NC}"
    
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
    
    print_status "Installation test completed"
}

# Clean up any existing scattered installation
cleanup_old_installation() {
    echo -e "${BLUE}Cleaning up old installations...${NC}"
    
    # Remove old home directory installation
    if [ -d "$HOME/trisonica" ]; then
        print_warning "Found old installation in home directory"
        echo "Remove old installation at $HOME/trisonica? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            rm -rf "$HOME/trisonica"
            print_status "Old installation removed"
        fi
    fi
    
    # Remove old log directory
    if [ -d "$HOME/Documents/TriSonica_Logs" ]; then
        print_warning "Found old log directory"
        echo "Move logs to project directory? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            mv "$HOME/Documents/TriSonica_Logs"/* "$LOG_DIR/" 2>/dev/null || true
            rmdir "$HOME/Documents/TriSonica_Logs" 2>/dev/null || true
            print_status "Logs moved to project directory"
        fi
    fi
}

# Main installation function
main() {
    echo -e "${BLUE}Starting macOS installation...${NC}"
    
    check_macos
    check_python
    cleanup_old_installation
    check_homebrew
    create_directories
    create_venv
    install_dependencies
    copy_files
    create_launchers
    test_installation
    
    echo
    echo -e "${GREEN}Installation complete!${NC}"
    echo
    echo "Usage:"
    echo "  Direct run:      ./run_trisonica.sh"
    echo "  Quick start:     ./quick_start.sh"
    echo "  View logs:       ./view_logs.sh"
    echo "  System info:     ./system_info.sh"
    echo
    echo "Files:"
    echo "  Application:     $INSTALL_DIR/"
    echo "  Logs:           $LOG_DIR/"
    echo "  Virtual env:    $VENV_DIR/"
    echo
    echo "Command line options:"
    echo "  Auto-detect:     ./run_trisonica.sh"
    echo "  Specific port:   ./run_trisonica.sh --port /dev/tty.usbserial-210"
    echo "  Show raw data:   ./run_trisonica.sh --show-raw"
    echo "  Custom log dir:  ./run_trisonica.sh --log-dir /path/to/logs"
    echo
    echo "Ready to start logging your Trisonica data!"
    echo
    echo "Would you like to run a quick test? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Running quick test...${NC}"
        ./quick_start.sh --help
    fi
}

# Run main installation
main "$@"