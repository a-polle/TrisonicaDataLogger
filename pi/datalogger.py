#!/usr/bin/env python3
"""
TriSonica Data Logger for Raspberry Pi
Optimized for headless operation and low resource usage
"""

import serial
import datetime
import time
import os
import sys
import signal
import re
import argparse
import glob
from collections import deque
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import logging

# Performance configuration optimized for Raspberry Pi
MAX_DATAPOINTS = 100   # Keep last N data points for display (reduced for Pi)
UPDATE_INTERVAL = 1.0  # Screen update interval (1s = 1 Hz, Pi-friendly)
LOG_ROTATION_SIZE = 10 * 1024 * 1024  # 10MB (SD card friendly)

@dataclass
class SerialConfig:
    port: str = 'auto'
    baud_rate: int = 115200
    timeout: float = 1.0
    
@dataclass    
class LoggingConfig:
    log_dir: str = "OUTPUT"
    max_log_size: int = LOG_ROTATION_SIZE
    save_stats: bool = True

class TrisonicaDataLoggerPi:
    def __init__(self, port: str = 'auto', log_dir: str = None):
        """
        Initialize the TriSonica data logger for Raspberry Pi.
        """
        self.port = port
        self.log_dir = log_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "OUTPUT")
        
        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(os.path.join(self.log_dir, 'datalogger.log'))
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize variables
        self.serial_connection = None
        self.log_file = None
        self.stats_file = None
        self.running = False
        self.data_count = 0
        self.start_time = None
        
        # CSV structure
        self.csv_columns = ['timestamp']
        self.csv_headers_written = False
        
        # Data storage for basic statistics (Pi-friendly small buffers)
        self.latest_data = {}
        self.parameter_stats = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def find_serial_ports(self) -> List[str]:
        """
        Find available serial ports using Raspberry Pi-specific patterns.
        """
        patterns = [
            '/dev/ttyUSB*',
            '/dev/ttyACM*'
        ]
        
        ports = []
        for pattern in patterns:
            ports.extend(glob.glob(pattern))
        
        return sorted(ports)
    
    def connect_serial(self) -> bool:
        """Connect to the serial port."""
        if self.port == 'auto':
            ports = self.find_serial_ports()
            
            if not ports:
                print("\nNo serial ports found!")
                print("Please check your USB connection.")
                self.logger.error("No serial ports found")
                return False
            
            print(f"\nFound {len(ports)} serial port(s):")
            for i, port in enumerate(ports, 1):
                print(f"  {i}. {port}")
            self.logger.info(f"Found {len(ports)} serial ports: {ports}")
            
            # Use the first available port
            selected_port = ports[0]
            print(f"Using port: {selected_port}")
            
        else:
            selected_port = self.port
            
        try:
            self.serial_connection = serial.Serial(
                port=selected_port,
                baudrate=115200,
                timeout=1.0,
                exclusive=True
            )
            
            print(f"Connected to {selected_port} at 115200 baud")
            self.logger.info(f"Serial connection established: {selected_port}")
            return True
            
        except serial.SerialException as e:
            print(f"Failed to connect to {selected_port}: {e}")
            self.logger.error(f"Serial connection failed: {e}")
            return False
    
    def setup_logging(self) -> bool:
        """Setup CSV logging files."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.log_filename = f"TrisonicaData_{timestamp}.csv"
        self.stats_filename = f"TrisonicaStats_{timestamp}.csv"
        
        try:
            # Open data log file
            self.log_file = open(os.path.join(self.log_dir, self.log_filename), 'w', newline='')
            
            # Open stats file
            self.stats_file = open(os.path.join(self.log_dir, self.stats_filename), 'w', newline='')
            self.stats_file.write("timestamp,parameter,min,max,mean,std_dev,count\n")
            self.stats_file.flush()
            
            print(f"Logging to: {self.log_filename}")
            self.logger.info(f"Log files created: {self.log_filename}, {self.stats_filename}")
            return True
            
        except Exception as e:
            print(f"Failed to create log files: {e}")
            self.logger.error(f"Failed to create log files: {e}")
            return False
    
    def parse_trisonica_data(self, line: str) -> Optional[Dict[str, str]]:
        """Parse a line of Trisonica data."""
        try:
            # Remove whitespace and split by commas
            parts = line.strip().split(',')
            
            if len(parts) < 2:
                return None
                
            parsed_data = {}
            
            # Parse each parameter
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                    
                # Split by space to get parameter and value
                tokens = part.split()
                if len(tokens) >= 2:
                    param = tokens[0]
                    value = tokens[1]
                    parsed_data[param] = value
                    
            return parsed_data if parsed_data else None
            
        except Exception as e:
            self.logger.debug(f"Error parsing line: {line.strip()}: {e}")
            return None
    
    def update_csv_columns(self, parsed_data: Dict[str, str]):
        """Update CSV columns based on new parameters found."""
        new_columns = False
        for key in parsed_data.keys():
            if key not in self.csv_columns:
                self.csv_columns.append(key)
                new_columns = True
        
        # Write headers if this is the first data or if new columns were added
        if not self.csv_headers_written:
            self.log_file.write(','.join(self.csv_columns) + '\n')
            self.csv_headers_written = True
            self.logger.info(f"CSV headers written: {self.csv_columns}")
    
    def write_csv_row(self, timestamp: datetime.datetime, parsed_data: Dict[str, str]):
        """Write a properly formatted CSV row."""
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
    
    def update_statistics(self, parsed_data: Dict[str, str]):
        """Update simple statistics for parameters."""
        for param, value_str in parsed_data.items():
            try:
                value = float(value_str)
                
                if param not in self.parameter_stats:
                    self.parameter_stats[param] = {
                        'min': value,
                        'max': value,
                        'sum': value,
                        'count': 1,
                        'values': deque(maxlen=100)  # Keep last 100 for std dev
                    }
                else:
                    stats = self.parameter_stats[param]
                    stats['min'] = min(stats['min'], value)
                    stats['max'] = max(stats['max'], value)
                    stats['sum'] += value
                    stats['count'] += 1
                    
                self.parameter_stats[param]['values'].append(value)
                    
            except (ValueError, TypeError):
                continue
    
    def save_statistics(self):
        """Save current statistics to file."""
        if not self.parameter_stats:
            return
            
        timestamp = datetime.datetime.now().isoformat()
        
        for param, stats in self.parameter_stats.items():
            if stats['count'] == 0:
                continue
                
            mean = stats['sum'] / stats['count']
            
            # Calculate standard deviation
            values = list(stats['values'])
            if len(values) > 1:
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                std_dev = variance ** 0.5
            else:
                std_dev = 0.0
            
            # Write to stats file
            self.stats_file.write(f"{timestamp},{param},{stats['min']:.6f},{stats['max']:.6f},{mean:.6f},{std_dev:.6f},{stats['count']}\n")
        
        self.stats_file.flush()
    
    def read_and_process_data(self) -> bool:
        """Read and process one line of data."""
        if not self.serial_connection or not self.serial_connection.is_open:
            return False
            
        try:
            # Read a line from serial
            line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
            
            if not line:
                return False
                
            # Parse the data
            parsed_data = self.parse_trisonica_data(line)
            
            if not parsed_data:
                return False
            
            # Update CSV structure if needed
            self.update_csv_columns(parsed_data)
            
            # Write to CSV
            timestamp = datetime.datetime.now()
            self.write_csv_row(timestamp, parsed_data)
            
            # Update statistics
            self.update_statistics(parsed_data)
            self.latest_data = parsed_data
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error reading serial data: {e}")
            return False
    
    def print_banner(self):
        """Print startup banner with system information."""
        banner_text = """
==============================================================
              TRISONICA DATA LOGGER - Raspberry Pi
==============================================================
        """
        
        system_info = f"""
System Information:
  Platform: Raspberry Pi
  Python: {sys.version.split()[0]}
  Log Directory: {self.log_dir}
  Port: {self.port if self.port != 'auto' else 'Auto-detect'}
  """
        
        print(banner_text)
        print(system_info)
        self.logger.info("TriSonica Data Logger started")
    
    def run(self):
        """Main execution loop for headless operation."""
        try:
            self.print_banner()
            
            # Connect to serial port
            if not self.connect_serial():
                return
            
            # Setup logging
            if not self.setup_logging():
                return
            
            print("\nStarting data collection...")
            print("Press Ctrl+C to stop\n")
            self.logger.info("Data collection started")
            
            # Simple headless data collection loop
            self.start_time = datetime.datetime.now()
            self.running = True
            last_status_time = time.time()
            last_stats_time = time.time()
            
            while self.running:
                try:
                    if self.read_and_process_data():
                        self.data_count += 1
                        
                        current_time = time.time()
                        
                        # Print status every 60 seconds
                        if current_time - last_status_time >= 60:
                            uptime = datetime.datetime.now() - self.start_time
                            rate = self.data_count / uptime.total_seconds() if uptime.total_seconds() > 0 else 0
                            print(f"Status: {self.data_count} data points collected, rate: {rate:.1f} Hz, file: {self.log_filename}")
                            self.logger.info(f"Status: {self.data_count} data points, rate: {rate:.1f} Hz")
                            last_status_time = current_time
                        
                        # Save statistics every 10 minutes
                        if current_time - last_stats_time >= 600:
                            self.save_statistics()
                            last_stats_time = current_time
                            
                    time.sleep(UPDATE_INTERVAL)
                except KeyboardInterrupt:
                    self.logger.info("Keyboard interrupt received")
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    time.sleep(1)
                        
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"\nFatal error: {e}")
            self.logger.error(f"Fatal error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources before exit."""
        self.running = False
        
        # Save final statistics
        if self.parameter_stats:
            self.save_statistics()
        
        if hasattr(self, 'log_file') and self.log_file:
            try:
                self.log_file.close()
                print(f"\nLog file saved: {self.log_filename}")
                self.logger.info(f"Log file saved: {self.log_filename}")
            except Exception as e:
                self.logger.error(f"Error closing log file: {e}")
        
        if hasattr(self, 'stats_file') and self.stats_file:
            try:
                self.stats_file.close()
                print(f"Stats file saved: {self.stats_filename}")
                self.logger.info(f"Stats file saved: {self.stats_filename}")
            except Exception as e:
                self.logger.error(f"Error closing stats file: {e}")
        
        if hasattr(self, 'serial_connection') and self.serial_connection:
            try:
                self.serial_connection.close()
                print("Serial connection closed")
                self.logger.info("Serial connection closed")
            except Exception as e:
                self.logger.error(f"Error closing serial connection: {e}")
                
        # Final statistics
        if hasattr(self, 'data_count') and hasattr(self, 'start_time') and self.start_time:
            uptime = datetime.datetime.now() - self.start_time
            print(f"\nFinal Statistics:")
            print(f"  Total data points: {self.data_count:,}")
            print(f"  Uptime: {str(uptime).split('.')[0]}")
            if uptime.total_seconds() > 0:
                rate = self.data_count / uptime.total_seconds()
                print(f"  Average rate: {rate:.2f} Hz")
            self.logger.info(f"Session completed: {self.data_count} data points, uptime {uptime}")
                
        print("\nGoodbye!")
        self.logger.info("TriSonica Data Logger stopped")

def main():
    parser = argparse.ArgumentParser(description='TriSonica Data Logger for Raspberry Pi')
    parser.add_argument('--port', default='auto', help='Serial port (default: auto-detect)')
    parser.add_argument('--log-dir', help='Directory for log files (default: OUTPUT)')
    
    args = parser.parse_args()
    
    # Create and run logger
    logger = TrisonicaDataLoggerPi(
        port=args.port,
        log_dir=args.log_dir
    )
    
    logger.run()

if __name__ == "__main__":
    main()