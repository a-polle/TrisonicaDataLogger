#!/usr/bin/env python3

import serial
import datetime
import time
import sys
import signal
import re
import os
import glob
import argparse
from collections import deque
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

# macOS optimized imports
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

# --- Configuration ---
DEFAULT_BAUD_RATE = 115200
MAX_DATAPOINTS = 1000  # More data points on Mac
UPDATE_INTERVAL = 0.05  # Faster updates on Mac
LOG_ROTATION_SIZE = 50 * 1024 * 1024  # 50MB logs on Mac

@dataclass
class Config:
    serial_port: str = "auto"
    baud_rate: int = DEFAULT_BAUD_RATE
    log_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OUTPUT")
    show_raw_data: bool = False
    save_statistics: bool = True
    plot_enabled: bool = False  # Future: real-time plotting
    max_log_size: int = LOG_ROTATION_SIZE

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
    values: deque = field(default_factory=lambda: deque(maxlen=100))

class TrisonicaDataLoggerMac:
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
        self.csv_columns = ['timestamp']  # Start with timestamp
        self.csv_headers_written = False
        
        # macOS specific
        self.last_update = time.time()
        self.update_rate = 0.0
        
        # Visualization data storage
        self.viz_data = {
            'wind_speed': deque(maxlen=50),      # S or S2 values
            'temperature': deque(maxlen=50),     # T values
            'wind_direction': deque(maxlen=50),  # D values
            'timestamps': deque(maxlen=50)       # For trend analysis
        }
        
        # Ensure log directory exists
        os.makedirs(config.log_dir, exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Print startup banner
        self.print_startup_banner()
        
    def print_startup_banner(self):
        """Print a nice startup banner"""
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║                 TRISONICA DATA LOGGER - macOS                ║
║                                                               ║
║  Optimized for macOS development and high-performance logging ║
╚═══════════════════════════════════════════════════════════════╝
"""
        self.console.print(banner, style="bold cyan")
        self.console.print(f"Platform: macOS")
        self.console.print(f"Python: {sys.version.split()[0]}")
        self.console.print(f"Log Directory: {self.config.log_dir}")
        self.console.print(f"Max Data Points: {MAX_DATAPOINTS:,}")
        self.console.print("─" * 60)
        
    def find_serial_ports(self) -> List[str]:
        """Find macOS serial ports"""
        patterns = [
            '/dev/tty.usbserial-*',
            '/dev/cu.usbserial-*',
            '/dev/tty.usbmodem*',
            '/dev/cu.usbmodem*'
        ]
        
        ports = []
        for pattern in patterns:
            ports.extend(glob.glob(pattern))
            
        return sorted(set(ports))
        
    def auto_detect_serial_port(self) -> Optional[str]:
        """Auto-detect Trisonica on macOS"""
        ports = self.find_serial_ports()
        
        if not ports:
            self.console.print("[ERROR] No serial ports found!", style="bold red")
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
                for _ in range(10):  # More attempts on Mac
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
                    return port
                else:
                    self.console.print(" [FAIL] No Trisonica data", style="dim")
                    
            except Exception as e:
                self.console.print(f" [ERROR] {e}", style="red")
                
        self.console.print("[WARNING] No Trisonica devices found", style="bold yellow")
        return None
        
    def setup_logging(self):
        """Setup enhanced logging for macOS"""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
        
        # Data log
        self.log_filename = f"TrisonicaData_{timestamp}.csv"
        self.log_path = os.path.join(self.config.log_dir, self.log_filename)
        self.log_file = open(self.log_path, 'w', newline='')
        # Headers will be written dynamically when first data arrives
        
        # Statistics log
        if self.config.save_statistics:
            self.stats_filename = f"TrisonicaStats_{timestamp}.csv"
            self.stats_path = os.path.join(self.config.log_dir, self.stats_filename)
            self.stats_file = open(self.stats_path, 'w', newline='')
            self.stats_file.write("timestamp,parameter,min,max,mean,std_dev,count\n")
            
        self.console.print(f"[LOG] Data Log: {self.log_filename}")
        if self.config.save_statistics:
            self.console.print(f"[LOG] Stats Log: {self.stats_filename}")
            
    def signal_handler(self, signum, frame):
        """Enhanced signal handler"""
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
            # Handle multiple possible formats
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
                # Space-separated format
                parts = line.strip().split()
                for i in range(0, len(parts)-1, 2):
                    if i+1 < len(parts):
                        parsed[parts[i]] = parts[i+1]
                        
        except Exception as e:
            # Log parsing errors but continue
            pass
            
        return parsed
    
    def update_csv_columns(self, parsed_data: Dict[str, str]):
        """Update CSV columns based on new parameters found"""
        new_columns = False
        for key in parsed_data.keys():
            if key not in self.csv_columns:
                self.csv_columns.append(key)
                new_columns = True
        
        # Write headers if this is the first data or if new columns were added
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
                # Get value for this column, or empty string if not present
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
            
            # Calculate mean
            stat.mean_val = sum(stat.values) / len(stat.values)
            
            # Calculate standard deviation
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
            
            # Update CSV columns and write properly formatted row
            self.update_csv_columns(parsed)
            self.write_csv_row(timestamp, parsed)
            
            # Update statistics
            for key, value_str in parsed.items():
                try:
                    value = float(value_str)
                    self.calculate_statistics(key, value)
                    
                    # Update visualization data
                    if key in ['S', 'S2']:  # Wind speed
                        self.viz_data['wind_speed'].append(value)
                    elif key == 'T':  # Temperature
                        self.viz_data['temperature'].append(value)
                    elif key == 'D':  # Wind direction
                        self.viz_data['wind_direction'].append(value)
                        
                except ValueError:
                    pass
                    
            # Update timestamps for visualization
            self.viz_data['timestamps'].append(timestamp)
                    
            # Calculate update rate
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
    
    def create_sparkline(self, data: deque, title: str) -> Panel:
        """Create a sparkline visualization"""
        if len(data) < 2:
            return Panel(f"[dim]Collecting {title} data...[/dim]", title=title)
        
        try:
            # Convert to list and ensure we have numeric data
            values = [float(x) for x in data if x is not None]
            if not values:
                return Panel(f"[dim]No {title} data[/dim]", title=title)
            
            # Create sparkline
            sparkline = Sparkline(values, width=30)
            
            # Add current value and trend
            current = values[-1]
            trend = "↗" if len(values) > 1 and values[-1] > values[-2] else "↘"
            
            content = f"{sparkline}\n[bold]{title}: {current:.2f}[/bold] {trend}"
            return Panel(content, title=title, border_style="bright_blue")
            
        except Exception as e:
            return Panel(f"[red]Error: {e}[/red]", title=title)
    
    def create_wind_compass(self, directions: deque) -> Panel:
        """Create ASCII wind compass"""
        if len(directions) < 1:
            return Panel("[dim]No wind direction data[/dim]", title="Wind Direction")
        
        try:
            current_dir = float(directions[-1])
            
            # Simple 8-point compass
            compass_points = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
            index = int((current_dir + 22.5) / 45) % 8
            direction = compass_points[index]
            
            # Create simple compass visualization
            compass = f"""
     N
   NW+NE
  W  +  E
   SW+SE
     S
     
Current: {current_dir:.0f}° ({direction})
"""
            return Panel(compass, title="Wind Direction", border_style="bright_green")
            
        except Exception as e:
            return Panel(f"[red]Error: {e}[/red]", title="Wind Direction")
    
    def create_trend_bars(self, data: deque, title: str, max_bars: int = 10) -> Panel:
        """Create trend bars visualization"""
        if len(data) < 2:
            return Panel(f"[dim]Collecting {title} data...[/dim]", title=title)
        
        try:
            # Get last few values
            values = [float(x) for x in list(data)[-max_bars:] if x is not None]
            if not values:
                return Panel(f"[dim]No {title} data[/dim]", title=title)
            
            # Normalize values to 0-1 range
            min_val, max_val = min(values), max(values)
            if max_val == min_val:
                normalized = [0.5] * len(values)
            else:
                normalized = [(v - min_val) / (max_val - min_val) for v in values]
            
            # Create vertical bars
            bars = []
            for i, norm_val in enumerate(normalized):
                bar_height = int(norm_val * 8)  # 8 levels
                bar = "█" * bar_height + "░" * (8 - bar_height)
                bars.append(f"{values[i]:.1f}\n{bar}")
            
            content = "\n".join(bars[-5:])  # Show last 5 bars
            return Panel(content, title=f"{title} Trend", border_style="bright_yellow")
            
        except Exception as e:
            return Panel(f"[red]Error: {e}[/red]", title=title)
        
    def create_layout(self) -> Layout:
        """Create enhanced layout for macOS"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=4)
        )
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        layout["left"].split_column(
            Layout(name="current_data", ratio=1),
            Layout(name="raw_data", size=8)
        )
        layout["right"].split_column(
            Layout(name="statistics", ratio=1),
            Layout(name="visualizations", ratio=1)
        )
        return layout
        
    def update_display(self, layout: Layout):
        """Enhanced display with more information"""
        # Header with system info
        elapsed = time.time() - self.start_time
        runtime = str(datetime.timedelta(seconds=int(elapsed)))
        
        header_table = Table.grid(expand=True)
        header_table.add_column(justify="left", ratio=1)
        header_table.add_column(justify="center", ratio=1)
        header_table.add_column(justify="right", ratio=1)
        
        # System metrics
        memory_usage = f"{sys.getsizeof(self.data_points) / 1024:.1f} KB"
        
        header_table.add_row(
            "Trisonica macOS Logger",
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
            
            # Live data table
            data_table = Table(title="Current Measurements", box=box.ROUNDED)
            data_table.add_column("Parameter", style="cyan", width=12)
            data_table.add_column("Value", style="green", width=10)
            data_table.add_column("Unit", style="dim", width=8)
            data_table.add_column("Quality", style="yellow", width=10)
            
            for key, value in latest.parsed_data.items():
                try:
                    val = float(value)
                    if key.startswith('S'):
                        unit = "m/s"
                        quality = "Good" if 0 <= val <= 50 else "Check"
                    elif key.startswith('T'):
                        unit = "°C"
                        quality = "Good" if -40 <= val <= 60 else "Check"
                    else:
                        unit = ""
                        quality = "Unknown"
                except:
                    unit = ""
                    quality = "Invalid"
                    
                data_table.add_row(key, value, unit, quality)
                
            layout["current_data"].update(Panel(data_table, title="Live Data"))
            
            # Raw data display
            if self.config.show_raw_data:
                raw_lines = []
                for dp in list(self.data_points)[-5:]:
                    timestamp = dp.timestamp.strftime('%H:%M:%S.%f')[:-3]
                    raw_lines.append(f"{timestamp}: {dp.raw_data}")
                    
                raw_text = "\n".join(raw_lines)
                layout["raw_data"].update(Panel(raw_text, title="Raw Data Stream"))
            else:
                layout["raw_data"].update(Panel("Raw data display disabled", title="Raw Data"))
                
        else:
            layout["current_data"].update(Panel("Waiting for data...", title="Live Data"))
            layout["raw_data"].update(Panel("No data received yet", title="Raw Data"))
            
        # Statistics panel
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
            
        # Visualizations panel
        if len(self.viz_data['wind_speed']) > 0:
            # Create visualizations
            viz_panels = []
            
            # Wind speed sparkline
            if self.viz_data['wind_speed']:
                wind_sparkline = self.create_sparkline(self.viz_data['wind_speed'], "Wind Speed")
                viz_panels.append(wind_sparkline)
            
            # Temperature sparkline
            if self.viz_data['temperature']:
                temp_sparkline = self.create_sparkline(self.viz_data['temperature'], "Temperature")
                viz_panels.append(temp_sparkline)
            
            # Wind direction compass
            if self.viz_data['wind_direction']:
                compass = self.create_wind_compass(self.viz_data['wind_direction'])
                viz_panels.append(compass)
            
            # Combine visualizations
            if viz_panels:
                # Simple approach: show first visualization panel
                if len(viz_panels) > 0:
                    layout["visualizations"].update(viz_panels[0])
                else:
                    layout["visualizations"].update(Panel("Collecting visualization data...", title="Live Visualizations"))
            else:
                layout["visualizations"].update(Panel("Collecting visualization data...", title="Live Visualizations"))
        else:
            layout["visualizations"].update(Panel("Collecting visualization data...", title="Live Visualizations"))
            
        # Footer
        footer_info = []
        footer_info.append(f"Data: {self.log_filename}")
        if self.config.save_statistics:
            footer_info.append(f"Stats: {self.stats_filename}")
        footer_info.append("Press Ctrl+C to exit")
        
        footer_text = " | ".join(footer_info)
        layout["footer"].update(Panel(Align.center(footer_text), style="dim"))
        
    def run(self):
        """Main execution with Rich interface"""
        if not self.connect_serial():
            return False
            
        layout = self.create_layout()
        
        try:
            with Live(layout, refresh_per_second=20, screen=True) as live:
                self.running = True
                while self.running:
                    data_point = self.read_serial_data()
                    if data_point:
                        self.point_count += 1
                        self.data_points.append(data_point)
                        
                        # Save statistics periodically
                        if self.point_count % 100 == 0:
                            self.save_final_statistics()
                            
                    self.update_display(layout)
                    time.sleep(UPDATE_INTERVAL)
                    
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
            
        return True
        
    def cleanup(self):
        """Enhanced cleanup"""
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
            
        self.console.print("[SUCCESS] Cleanup complete", style="bold green")

def main():
    parser = argparse.ArgumentParser(description='Trisonica Data Logger for macOS')
    parser.add_argument('--port', default='auto', help='Serial port (default: auto-detect)')
    parser.add_argument('--baud', type=int, default=DEFAULT_BAUD_RATE, help='Baud rate')
    parser.add_argument('--log-dir', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "OUTPUT"), help='Log directory')
    parser.add_argument('--show-raw', action='store_true', help='Show raw data stream')
    parser.add_argument('--no-stats', action='store_true', help='Disable statistics logging')
    
    args = parser.parse_args()
    
    config = Config(
        serial_port=args.port,
        baud_rate=args.baud,
        log_dir=args.log_dir,
        show_raw_data=args.show_raw,
        save_statistics=not args.no_stats
    )
    
    logger = TrisonicaDataLoggerMac(config)
    sys.exit(0 if logger.run() else 1)

if __name__ == '__main__':
    main()
