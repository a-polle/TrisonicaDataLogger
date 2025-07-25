#!/usr/bin/env python3
"""
TriSonica Data Logger for Windows
Optimized for Windows desktop environments with enhanced GUI features
"""

import serial
import datetime
import time
import sys
import signal
import re
import os
import glob
import argparse
import threading
from collections import deque
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

# Windows optimized imports
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.text import Text
from rich.align import Align
from rich import box
from rich.columns import Columns
from rich.tree import Tree
from rich.sparkline import Sparkline
from rich.bar import Bar

# Windows specific imports
import winsound
import win32api

# --- Configuration ---
DEFAULT_BAUD_RATE = 115200
MAX_DATAPOINTS = 2000  # More data points on Windows
UPDATE_INTERVAL = 0.03  # Fastest updates on Windows
LOG_ROTATION_SIZE = 100 * 1024 * 1024  # 100MB logs on Windows

@dataclass
class Config:
    serial_port: str = "auto"
    baud_rate: int = DEFAULT_BAUD_RATE
    log_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OUTPUT")
    show_raw_data: bool = False
    save_statistics: bool = True
    plot_enabled: bool = False
    max_log_size: int = LOG_ROTATION_SIZE
    enable_sound: bool = True

@dataclass
class DataPoint:
    timestamp: datetime.datetime
    raw_data: str
    parsed_data: Dict[str, str] = field(default_factory=dict)

@dataclass
class Statistics:
    min_val: float = 0.0
    max_val: float = 0.0
    mean_val: float = 0.0
    current_val: float = 0.0
    std_dev: float = 0.0
    count: int = 0
    values: deque = field(default_factory=lambda: deque(maxlen=200))

class TrisonicaDataLoggerWindows:
    def __init__(self, config: Config):
        self.config = config
        self.serial_port = None
        self.log_file = None
        self.stats_file = None
        self.console = Console()
        self.running = False
        self.start_time = time.time()
        
        # Data storage
        self.data_points = deque(maxlen=MAX_DATAPOINTS)
        self.point_count = 0
        self.stats = {}
        
        # CSV column management
        self.csv_columns = ['timestamp']
        self.csv_headers_written = False
        
        # Windows specific
        self.last_update = time.time()
        self.update_rate = 0.0
        self.system_info = self.get_system_info()
        
        # Visualization data storage
        self.viz_data = {
            'wind_speed': deque(maxlen=100),
            'temperature': deque(maxlen=100),
            'wind_direction': deque(maxlen=100),
            'timestamps': deque(maxlen=100)
        }
        
        # Ensure log directory exists
        os.makedirs(config.log_dir, exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Signal handlers (Windows compatible)
        signal.signal(signal.SIGINT, self.signal_handler)
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, self.signal_handler)
        
        # Print startup banner
        self.print_startup_banner()

    def get_system_info(self) -> Dict[str, str]:
        """Get Windows system information"""
        try:
            computer_name = win32api.GetComputerName()
            user_name = win32api.GetUserName()
            
            return {
                'computer_name': computer_name,
                'user_name': user_name,
                'platform': 'Windows',
                'python_version': sys.version.split()[0]
            }
        except:
            return {
                'computer_name': 'Unknown',
                'user_name': 'Unknown', 
                'platform': 'Windows',
                'python_version': sys.version.split()[0]
            }
        
    def print_startup_banner(self):
        """Print Windows startup banner"""
        banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║                TRISONICA DATA LOGGER - Windows                   ║
║                                                                  ║
║    Optimized for Windows desktop with enhanced GUI features     ║
║                                                                  ║
║  Computer: {self.system_info['computer_name']:<20} User: {self.system_info['user_name']:<20}║
╚══════════════════════════════════════════════════════════════════╝
"""
        self.console.print(banner, style="bold cyan")
        self.console.print(f"Platform: {self.system_info['platform']}")
        self.console.print(f"Python: {self.system_info['python_version']}")
        self.console.print(f"Log Directory: {self.config.log_dir}")
        self.console.print(f"Max Data Points: {MAX_DATAPOINTS:,}")
        self.console.print(f"Sound Alerts: {'Enabled' if self.config.enable_sound else 'Disabled'}")
        self.console.print("─" * 70)
        
    def find_serial_ports(self) -> List[str]:
        """Find Windows serial ports"""
        import serial.tools.list_ports
        
        ports = []
        for port_info in serial.tools.list_ports.comports():
            ports.append(port_info.device)
            
        return sorted(ports)
        
    def auto_detect_serial_port(self) -> Optional[str]:
        """Auto-detect Trisonica on Windows"""
        ports = self.find_serial_ports()
        
        if not ports:
            self.console.print("[ERROR] No serial ports found!", style="bold red")
            if self.config.enable_sound:
                try:
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                except:
                    pass
            return None
            
        self.console.print(f"[INFO] Found {len(ports)} serial port(s):")
        for i, port in enumerate(ports):
            self.console.print(f"  {i+1}. {port}")
            
        # Test each port
        for port in ports:
            try:
                self.console.print(f"[TEST] Testing {port}...", end="")
                ser = serial.Serial(port, self.config.baud_rate, timeout=2)
                
                # Read several lines to detect Trisonica
                trisonica_detected = False
                for _ in range(15):  # More attempts on Windows
                    try:
                        line = ser.readline().decode('ascii', errors='ignore').strip()
                        if line and any(param in line for param in ['S1', 'S2', 'S3', 'T1', 'T2']):
                            trisonica_detected = True
                            break
                    except:
                        continue
                        
                ser.close()
                
                if trisonica_detected:
                    self.console.print(" [SUCCESS] Trisonica detected!", style="bold green")
                    if self.config.enable_sound:
                        try:
                            winsound.MessageBeep(winsound.MB_OK)
                        except:
                            pass
                    return port
                else:
                    self.console.print(" [FAIL] No Trisonica data", style="dim")
                    
            except Exception as e:
                self.console.print(f" [ERROR] {e}", style="red")
                
        self.console.print("[WARNING] No Trisonica devices found", style="bold yellow")
        if self.config.enable_sound:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except:
                pass
        return None
        
    def setup_logging(self):
        """Setup enhanced logging for Windows"""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
        
        # Data log
        self.log_filename = f"TrisonicaData_{timestamp}.csv"
        self.log_path = os.path.join(self.config.log_dir, self.log_filename)
        self.log_file = open(self.log_path, 'w', newline='', encoding='utf-8')
        
        # Statistics log
        if self.config.save_statistics:
            self.stats_filename = f"TrisonicaStats_{timestamp}.csv"
            self.stats_path = os.path.join(self.config.log_dir, self.stats_filename)
            self.stats_file = open(self.stats_path, 'w', newline='', encoding='utf-8')
            self.stats_file.write("timestamp,parameter,min,max,mean,std_dev,count\n")
            
        self.console.print(f"[LOG] Data Log: {self.log_filename}")
        if self.config.save_statistics:
            self.console.print(f"[LOG] Stats Log: {self.stats_filename}")
            
    def signal_handler(self, signum, frame):
        """Enhanced signal handler for Windows"""
        self.console.print(f"\n[SHUTDOWN] Received signal {signum}, saving data and shutting down...", style="bold yellow")
        self.save_final_statistics()
        self.running = False
        
    def connect_serial(self) -> bool:
        """Connect with enhanced error handling"""
        if self.config.serial_port == "auto":
            port = self.auto_detect_serial_port()
            if not port:
                return False
        else:
            port = self.config.serial_port
            
        try:
            self.serial_port = serial.Serial(port, self.config.baud_rate, timeout=1)
            self.console.print(f"[SUCCESS] Connected to {port} at {self.config.baud_rate:,} baud", style="bold green")
            return True
        except serial.SerialException as e:
            self.console.print(f"[ERROR] Connection failed: {e}", style="bold red")
            return False
            
    def parse_data_line(self, line: str) -> Dict[str, str]:
        """Enhanced parsing with better error handling"""
        parsed = {}
        try:
            if ',' in line:
                pairs = line.strip().split(',')
                for pair in pairs:
                    pair = pair.strip()
                    if ' ' in pair:
                        parts = pair.split(' ', 1)
                        if len(parts) == 2:
                            key, value = parts
                            parsed[key.strip()] = value.strip()
            else:
                parts = line.strip().split()
                for i in range(0, len(parts)-1, 2):
                    if i+1 < len(parts):
                        parsed[parts[i]] = parts[i+1]
                        
        except Exception as e:
            pass
            
        return parsed
    
    def update_csv_columns(self, parsed_data: Dict[str, str]):
        """Update CSV columns based on new parameters found"""
        new_columns = False
        for key in parsed_data.keys():
            if key not in self.csv_columns:
                self.csv_columns.append(key)
                new_columns = True
        
        if not self.csv_headers_written:
            self.log_file.write(','.join(self.csv_columns) + '\n')
            self.csv_headers_written = True
            
    def write_csv_row(self, timestamp: datetime.datetime, parsed_data: Dict[str, str]):
        """Write a properly formatted CSV row"""
        row_values = []
        for column in self.csv_columns:
            if column == 'timestamp':
                row_values.append(timestamp.isoformat())
            else:
                value = parsed_data.get(column, '')
                row_values.append(value)
        
        self.log_file.write(','.join(row_values) + '\n')
        self.log_file.flush()
        
    def calculate_statistics(self, key: str, value: float):
        """Enhanced statistics with standard deviation"""
        if key not in self.stats:
            self.stats[key] = Statistics()
            
        stat = self.stats[key]
        stat.current_val = value
        stat.count += 1
        stat.values.append(value)
        
        if stat.count == 1:
            stat.min_val = stat.max_val = stat.mean_val = value
            stat.std_dev = 0.0
        else:
            stat.min_val = min(stat.min_val, value)
            stat.max_val = max(stat.max_val, value)
            
            stat.mean_val = sum(stat.values) / len(stat.values)
            
            if len(stat.values) > 1:
                variance = sum((x - stat.mean_val) ** 2 for x in stat.values) / len(stat.values)
                stat.std_dev = variance ** 0.5
                
    def read_serial_data(self) -> Optional[DataPoint]:
        """Enhanced data reading with performance metrics"""
        if not self.serial_port or not self.serial_port.is_open:
            return None
            
        try:
            line = self.serial_port.readline().decode('ascii', errors='ignore').strip()
            if not line:
                return None
                
            timestamp = datetime.datetime.now()
            parsed = self.parse_data_line(line)
            
            self.update_csv_columns(parsed)
            self.write_csv_row(timestamp, parsed)
            
            for key, value_str in parsed.items():
                try:
                    value = float(value_str)
                    self.calculate_statistics(key, value)
                    
                    if key in ['S', 'S2']:
                        self.viz_data['wind_speed'].append(value)
                    elif key == 'T':
                        self.viz_data['temperature'].append(value)
                    elif key == 'D':
                        self.viz_data['wind_direction'].append(value)
                        
                except ValueError:
                    pass
                    
            self.viz_data['timestamps'].append(timestamp)
                    
            now = time.time()
            if now - self.last_update > 0:
                self.update_rate = 1.0 / (now - self.last_update)
            self.last_update = now
            
            return DataPoint(timestamp, line, parsed)
            
        except Exception as e:
            return None
            
    def save_final_statistics(self):
        """Save final statistics summary"""
        if not self.config.save_statistics or not self.stats_file:
            return
            
        timestamp = datetime.datetime.now().isoformat()
        for key, stat in self.stats.items():
            self.stats_file.write(f"{timestamp},{key},{stat.min_val:.6f},{stat.max_val:.6f},"
                                f"{stat.mean_val:.6f},{stat.std_dev:.6f},{stat.count}\n")
        self.stats_file.flush()
    
    def create_layout(self) -> Layout:
        """Create enhanced Windows layout"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=5)
        )
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        layout["left"].split_column(
            Layout(name="current_data", ratio=2),
            Layout(name="raw_data", size=10)
        )
        layout["right"].split_column(
            Layout(name="statistics", ratio=1),
            Layout(name="system_info", size=10)
        )
        return layout
        
    def update_display(self, layout: Layout):
        """Enhanced Windows display"""
        elapsed = time.time() - self.start_time
        runtime = str(datetime.timedelta(seconds=int(elapsed)))
        
        # Header
        header_table = Table.grid(expand=True)
        header_table.add_column(justify="left", ratio=1)
        header_table.add_column(justify="center", ratio=1)
        header_table.add_column(justify="right", ratio=1)
        
        memory_usage = f"{sys.getsizeof(self.data_points) / 1024:.1f} KB"
        
        header_table.add_row(
            f"Trisonica Windows Logger - {self.system_info['computer_name']}",
            f"Runtime: {runtime}",
            f"Points: {self.point_count:,}"
        )
        header_table.add_row(
            f"Update Rate: {self.update_rate:.1f} Hz",
            f"Memory: {memory_usage}",
            f"Log: {os.path.basename(self.log_path)}"
        )
        
        layout["header"].update(Panel(header_table, title="System Status", style="bold blue"))
        
        # Current data
        if self.data_points:
            latest = self.data_points[-1]
            
            data_table = Table(title="Current Measurements", box=box.ROUNDED)
            data_table.add_column("Parameter", style="cyan", width=12)
            data_table.add_column("Value", style="green", width=12)
            data_table.add_column("Unit", style="dim", width=10)
            data_table.add_column("Quality", style="yellow", width=12)
            
            for key, value in latest.parsed_data.items():
                try:
                    val = float(value)
                    if key.startswith('S'):
                        unit = "m/s"
                        quality = "Excellent" if 0 <= val <= 50 else "Check Range"
                    elif key.startswith('T'):
                        unit = "°C"
                        quality = "Excellent" if -40 <= val <= 60 else "Check Range"
                    else:
                        unit = ""
                        quality = "Unknown"
                except:
                    unit = ""
                    quality = "Invalid"
                    
                data_table.add_row(key, value, unit, quality)
                
            layout["current_data"].update(Panel(data_table, title="Live Data"))
            
            # Raw data
            if self.config.show_raw_data:
                raw_lines = []
                for dp in list(self.data_points)[-8:]:
                    timestamp = dp.timestamp.strftime('%H:%M:%S.%f')[:-3]
                    raw_lines.append(f"{timestamp}: {dp.raw_data}")
                    
                raw_text = "\n".join(raw_lines)
                layout["raw_data"].update(Panel(raw_text, title="Raw Data Stream"))
            else:
                layout["raw_data"].update(Panel("Raw data display disabled\nUse --show-raw to enable", title="Raw Data"))
                
        else:
            layout["current_data"].update(Panel("Waiting for data...", title="Live Data"))
            layout["raw_data"].update(Panel("No data received yet", title="Raw Data"))
            
        # Statistics
        if self.stats:
            stats_table = Table(title="Statistical Analysis", box=box.ROUNDED)
            stats_table.add_column("Parameter", style="cyan")
            stats_table.add_column("Current", style="green")
            stats_table.add_column("Min", style="blue")
            stats_table.add_column("Max", style="red")
            stats_table.add_column("Mean", style="yellow")
            stats_table.add_column("Std Dev", style="magenta")
            stats_table.add_column("Count", style="white")
            
            for key, stat in self.stats.items():
                stats_table.add_row(
                    key,
                    f"{stat.current_val:.3f}",
                    f"{stat.min_val:.3f}",
                    f"{stat.max_val:.3f}",
                    f"{stat.mean_val:.3f}",
                    f"{stat.std_dev:.3f}",
                    f"{stat.count:,}"
                )
                
            layout["statistics"].update(Panel(stats_table, title="Statistics"))
        else:
            layout["statistics"].update(Panel("No statistics available", title="Statistics"))
            
        # System info
        system_table = Table(title="System Info", box=box.SIMPLE)
        system_table.add_column("Property", style="cyan")
        system_table.add_column("Value", style="white")
        
        system_table.add_row("Computer", self.system_info['computer_name'])
        system_table.add_row("User", self.system_info['user_name'])
        system_table.add_row("Platform", self.system_info['platform'])
        system_table.add_row("Python", self.system_info['python_version'])
        
        layout["system_info"].update(Panel(system_table, title="System Information"))
            
        # Footer
        footer_info = []
        footer_info.append(f"Data: {self.log_filename}")
        if self.config.save_statistics:
            footer_info.append(f"Stats: {self.stats_filename}")
        footer_info.append("Press Ctrl+C or Ctrl+Break to exit")
        
        footer_text = " | ".join(footer_info)
        layout["footer"].update(Panel(Align.center(footer_text), style="dim"))
        
    def run(self):
        """Main execution with Windows-optimized interface"""
        if not self.connect_serial():
            return False
            
        layout = self.create_layout()
        
        try:
            with Live(layout, refresh_per_second=30, screen=True) as live:
                self.running = True
                while self.running:
                    data_point = self.read_serial_data()
                    if data_point:
                        self.point_count += 1
                        self.data_points.append(data_point)
                        
                        # Save statistics periodically
                        if self.point_count % 250 == 0:
                            self.save_final_statistics()
                            
                    self.update_display(layout)
                    time.sleep(UPDATE_INTERVAL)
                    
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
            
        return True
        
    def cleanup(self):
        """Enhanced Windows cleanup"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.console.print("[CLEANUP] Serial port closed", style="green")
            
        if self.log_file and not self.log_file.closed:
            self.log_file.close()
            self.console.print(f"[CLEANUP] Data log saved: {self.log_path}", style="green")
            
        if self.stats_file and not self.stats_file.closed:
            self.stats_file.close()
            self.console.print(f"[CLEANUP] Statistics saved: {self.stats_path}", style="green")
            
        # Final summary
        if self.point_count > 0:
            elapsed = time.time() - self.start_time
            avg_rate = self.point_count / elapsed if elapsed > 0 else 0
            self.console.print(f"\n[SUMMARY] Session Summary:")
            self.console.print(f"   Total Points: {self.point_count:,}")
            self.console.print(f"   Runtime: {datetime.timedelta(seconds=int(elapsed))}")
            self.console.print(f"   Average Rate: {avg_rate:.1f} Hz")
            self.console.print(f"   Data Quality: {len(self.stats)} parameters tracked")
            
            if self.config.enable_sound:
                try:
                    winsound.MessageBeep(winsound.MB_OK)
                except:
                    pass
            
        self.console.print("[SUCCESS] Cleanup complete", style="bold green")

def main():
    parser = argparse.ArgumentParser(description='Trisonica Data Logger for Windows')
    parser.add_argument('--port', default='auto', help='Serial port (default: auto-detect)')
    parser.add_argument('--baud', type=int, default=DEFAULT_BAUD_RATE, help='Baud rate')
    parser.add_argument('--log-dir', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "OUTPUT"), help='Log directory')
    parser.add_argument('--show-raw', action='store_true', help='Show raw data stream')
    parser.add_argument('--no-stats', action='store_true', help='Disable statistics logging')
    parser.add_argument('--no-sound', action='store_true', help='Disable sound alerts')
    
    args = parser.parse_args()
    
    config = Config(
        serial_port=args.port,
        baud_rate=args.baud,
        log_dir=args.log_dir,
        show_raw_data=args.show_raw,
        save_statistics=not args.no_stats,
        enable_sound=not args.no_sound
    )
    
    logger = TrisonicaDataLoggerWindows(config)
    sys.exit(0 if logger.run() else 1)

if __name__ == '__main__':
    main()