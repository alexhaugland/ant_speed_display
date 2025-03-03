#!./venv/bin/python3
"""
ANT+ Speed Display for Fitness Equipment
Displays speed data and distance traveled from ANT+ fitness equipment in large text on the terminal
Specifically looks for devices with ID 13500 by default
Uses imperial units (mph and miles)
"""

import sys
import time
import os
import signal
import argparse
import sqlite3
from datetime import datetime
import logging
from typing import Optional, Dict, List, Callable, Any, Tuple
from pathlib import Path

try:
    from openant.easy.node import Node
    from openant.devices import ANTPLUS_NETWORK_KEY
    from openant.devices.fitness_equipment import FitnessEquipment, FitnessEquipmentData
except ImportError:
    print("Error: Required libraries not found.")
    print("Please install the required packages with: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.WARN, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ant_scanner')

# Default target device ID
DEFAULT_DEVICE_ID = 13500

# Conversion constants
KM_TO_MILES = 0.621371  # Conversion factor from kilometers to miles
MS_TO_KMH = 3.6  # Conversion factor from m/s to km/h

# Database constants
DEFAULT_DB_PATH = os.path.expanduser("~/.ant_speed_display.db")
DB_TABLE_NAME = "daily_distance"

# ASCII art numbers for big text display
BIG_NUMBERS = {
    '0': [
        "  ███  ",
        " █   █ ",
        "█     █",
        "█     █",
        "█     █",
        " █   █ ",
        "  ███  "
    ],
    '1': [
        "   █   ",
        "  ██   ",
        " █ █   ",
        "   █   ",
        "   █   ",
        "   █   ",
        " █████ "
    ],
    '2': [
        " ████  ",
        "█    █ ",
        "     █ ",
        "  ███  ",
        " █     ",
        "█      ",
        "██████ "
    ],
    '3': [
        " ████  ",
        "█    █ ",
        "     █ ",
        "  ███  ",
        "     █ ",
        "█    █ ",
        " ████  "
    ],
    '4': [
        "█   █  ",
        "█   █  ",
        "█   █  ",
        "██████ ",
        "    █  ",
        "    █  ",
        "    █  "
    ],
    '5': [
        "██████ ",
        "█      ",
        "█      ",
        "█████  ",
        "     █ ",
        "█    █ ",
        " ████  "
    ],
    '6': [
        "  ███  ",
        " █     ",
        "█      ",
        "█████  ",
        "█    █ ",
        "█    █ ",
        " ████  "
    ],
    '7': [
        "██████ ",
        "     █ ",
        "    █  ",
        "   █   ",
        "  █    ",
        " █     ",
        "█      "
    ],
    '8': [
        " ████  ",
        "█    █ ",
        "█    █ ",
        " ████  ",
        "█    █ ",
        "█    █ ",
        " ████  "
    ],
    '9': [
        " ████  ",
        "█    █ ",
        "█    █ ",
        " █████ ",
        "     █ ",
        "    █  ",
        " ███   "
    ],
    '.': [
        "       ",
        "       ",
        "       ",
        "       ",
        "       ",
        "   ██  ",
        "   ██  "
    ],
    ' ': [
        "       ",
        "       ",
        "       ",
        "       ",
        "       ",
        "       ",
        "       "
    ]
}


class Database:
    """Database manager for storing daily distance data."""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize the database connection."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self) -> bool:
        """Connect to the SQLite database."""
        try:
            # Create directory if it doesn't exist
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                
            # Connect to database
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Create tables if they don't exist
            self._create_tables()
            return True
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            return False
    
    def _create_tables(self) -> None:
        """Create necessary tables if they don't exist."""
        try:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {DB_TABLE_NAME} (
                    date TEXT PRIMARY KEY,
                    device_id INTEGER NOT NULL,
                    distance REAL NOT NULL,
                    last_updated TIMESTAMP NOT NULL
                )
            ''')
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
    
    def _cleanup_old_data(self) -> None:
        """Remove data older than yesterday."""
        try:
            # Get today and yesterday's dates in ISO format (YYYY-MM-DD)
            today = datetime.now().date().isoformat()
            yesterday = (datetime.now().date() - datetime.timedelta(days=1)).isoformat()
            
            # Delete all records except today and yesterday
            self.cursor.execute(
                f"DELETE FROM {DB_TABLE_NAME} WHERE date != ? AND date != ?",
                (today, yesterday)
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def get_today_distance(self, device_id: int) -> float:
        """Get the total distance for today with this device."""
        try:
            today = datetime.now().date().isoformat()
            self.cursor.execute(
                f"SELECT distance FROM {DB_TABLE_NAME} WHERE date = ? AND device_id = ?",
                (today, device_id)
            )
            result = self.cursor.fetchone()
            return result[0] if result else 0.0
        except Exception as e:
            logger.error(f"Error getting today's distance: {e}")
            return 0.0
    
    def get_yesterday_distance(self, device_id: int) -> float:
        """Get the total distance for yesterday with this device."""
        try:
            yesterday = (datetime.now().date() - datetime.timedelta(days=1)).isoformat()
            self.cursor.execute(
                f"SELECT distance FROM {DB_TABLE_NAME} WHERE date = ? AND device_id = ?",
                (yesterday, device_id)
            )
            result = self.cursor.fetchone()
            return result[0] if result else 0.0
        except Exception as e:
            logger.error(f"Error getting yesterday's distance: {e}")
            return 0.0
    
    def update_today_distance(self, device_id: int, distance: float) -> bool:
        """Update today's distance if the new distance is significant (> 0.02 miles)."""
        if distance <= 0.02:
            logger.debug(f"Distance {distance} is too small to record (≤ 0.02 miles)")
            return False
            
        try:
            today = datetime.now().date().isoformat()
            now = datetime.now()
            
            # Check if we already have a record for today
            self.cursor.execute(
                f"SELECT distance FROM {DB_TABLE_NAME} WHERE date = ? AND device_id = ?",
                (today, device_id)
            )
            result = self.cursor.fetchone()
            
            if result:
                # Update existing record
                self.cursor.execute(
                    f"UPDATE {DB_TABLE_NAME} SET distance = distance + ?, last_updated = ? WHERE date = ? AND device_id = ?",
                    (distance, now, today, device_id)
                )
            else:
                # Insert new record
                self.cursor.execute(
                    f"INSERT INTO {DB_TABLE_NAME} (date, device_id, distance, last_updated) VALUES (?, ?, ?, ?)",
                    (today, device_id, distance, now)
                )
            
            self.conn.commit()
            
            # Clean up old data
            self._cleanup_old_data()
            return True
        except Exception as e:
            logger.error(f"Error updating today's distance: {e}")
            return False
    
    def get_stats(self) -> List[Tuple]:
        """Get statistics for today and yesterday."""
        try:
            today = datetime.now().date().isoformat()
            yesterday = (datetime.now().date() - datetime.timedelta(days=1)).isoformat()
            
            self.cursor.execute(
                f"SELECT device_id, date, distance, last_updated FROM {DB_TABLE_NAME} "
                f"WHERE date = ? OR date = ? ORDER BY date DESC, device_id",
                (today, yesterday)
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return []
    
    def close(self) -> None:
        """Close the database connection."""
        try:
            if self.conn:
                self.conn.close()
        except Exception as e:
            logger.error(f"Error closing database: {e}")


class SpeedDisplayApp:
    """Main application class for ANT+ Speed Display."""
    
    def __init__(self, device_id: int = DEFAULT_DEVICE_ID, db_path: str = DEFAULT_DB_PATH):
        """Initialize the application with the specified device ID."""
        self.device_id = device_id
        self.node: Optional[Node] = None
        self.fitness_equipment: Optional[FitnessEquipment] = None
        self.exit_flag = False
        self.total_distance = 0.0  # Total distance in miles for current session
        self.last_update_time: Optional[float] = None  # Last time we received speed data
        self.current_speed = 0.0  # Current speed in mph
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.reconnect_delay = 2  # seconds
        
        # Statistics tracking
        self.max_speed = 0.0
        self.speed_sum = 0.0
        self.speed_count = 0
        self.session_start_time = time.time()
        
        # Database setup
        self.db = Database(db_path)
        self.db_connected = self.db.connect()
        
        if self.db_connected:
            # Load today's and yesterday's distance
            self.today_distance = self.db.get_today_distance(device_id)
            self.yesterday_distance = self.db.get_yesterday_distance(device_id)
        else:
            self.today_distance = 0.0
            self.yesterday_distance = 0.0
            logger.warning("Database connection failed. Distance will not be saved.")
        
        # Set up signal handler for clean exit
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def display_big_text(self, speed_text: str, distance_text: str) -> None:
        """Display speed and distance in big ASCII art with units in small text."""
        # Clear the terminal
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Convert speed and distance to big ASCII art
        speed_lines = [""] * 7
        for char in speed_text:
            if char in BIG_NUMBERS:
                for i in range(7):
                    speed_lines[i] += BIG_NUMBERS[char][i] + " "
            else:
                # For characters not in our dictionary, use space
                for i in range(7):
                    speed_lines[i] += BIG_NUMBERS[' '][i] + " "
        
        distance_lines = [""] * 7
        for char in distance_text:
            if char in BIG_NUMBERS:
                for i in range(7):
                    distance_lines[i] += BIG_NUMBERS[char][i] + " "
            else:
                # For characters not in our dictionary, use space
                for i in range(7):
                    distance_lines[i] += BIG_NUMBERS[' '][i] + " "
        
        # Print the big text with headers and units
        print("\n" * 2)  # Add some space at the top
        
        # Print speed header
        print("SPEED:")
        
        # Print speed with units
        for i, line in enumerate(speed_lines):
            if i == 3:  # Middle line, add units
                print(f"{line}  mph")
            else:
                print(line)
        
        print("\n")  # Add space between speed and distance
        
        # Print distance header
        print("DISTANCE (session / today / yesterday):")
        
        # Print distance with units
        for i, line in enumerate(distance_lines):
            if i == 3:  # Middle line, add units
                print(f"{line}  mi / {self.today_distance + self.total_distance:.2f} mi / {self.yesterday_distance:.2f} mi")
            else:
                print(line)
        
        print("\n")  # Add some space at the bottom
    
    def calculate_distance(self, speed_mph: float, elapsed_seconds: float) -> float:
        """Calculate distance traveled based on speed and time."""
        # Convert mph to miles/second, then multiply by elapsed seconds
        return (speed_mph / 3600.0) * elapsed_seconds
    
    def update_display(self) -> None:
        """Update the terminal display with current speed and distance."""
        try:
            # Format speed to 2 decimal places
            speed_text = f"{self.current_speed:.2f}"
            
            # Format distance to 2 decimal places
            distance_text = f"{self.total_distance:.2f}"
            
            # Display both speed and distance
            self.display_big_text(speed_text, distance_text)
        except Exception as e:
            logger.error(f"Error updating display: {e}")
    
    def update_statistics(self) -> None:
        """Update workout statistics."""
        try:
            # Update max speed
            if self.current_speed > self.max_speed:
                self.max_speed = self.current_speed
            
            # Update average speed calculation
            self.speed_sum += self.current_speed
            self.speed_count += 1
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    def on_fitness_equipment_data(self, page: int, page_name: str, data: FitnessEquipmentData) -> None:
        """Callback for receiving fitness equipment data."""
        try:
            # Only process data if it's from the general_fe page (page 16)
            if page_name == "general_fe":
                # Get current time
                current_time = time.time()
                
                # Convert speed from m/s to mph
                # First convert to km/h (multiply by 3.6), then to mph (multiply by KM_TO_MILES)
                self.current_speed = data.speed * MS_TO_KMH * KM_TO_MILES
                
                # Calculate distance if we have a previous update
                if self.last_update_time is not None:
                    elapsed_seconds = current_time - self.last_update_time
                    distance = self.calculate_distance(self.current_speed, elapsed_seconds)
                    self.total_distance += distance
                
                # Update last update time
                self.last_update_time = current_time
                
                # Update statistics
                self.update_statistics()
                
                # Update display
                self.update_display()
        except Exception as e:
            logger.error(f"Error processing fitness equipment data: {e}")
    
    def on_device_found(self) -> None:
        """Callback when a device is found."""
        if self.fitness_equipment:
            print(f"\nDevice found: {self.fitness_equipment.name} (ID: {self.fitness_equipment.device_id})")
            print("Waiting for speed data...")
            # Reset connection attempts on successful connection
            self.connection_attempts = 0
    
    def _signal_handler(self, sig, frame) -> None:
        """Handle Ctrl+C gracefully."""
        self.exit_flag = True
        print("\nExiting...", end="", flush=True)
        self.cleanup()
        print(" Done!")
        
        # Show final stats
        print(f"\nFinal Stats:")
        print(f"Session Distance: {self.total_distance:.2f} miles")
        print(f"Today's Total Distance: {self.today_distance + self.total_distance:.2f} miles")
        print(f"Yesterday's Distance: {self.yesterday_distance:.2f} miles")
        print(f"Last Speed: {self.current_speed:.2f} mph")
        print(f"Max Speed: {self.max_speed:.2f} mph")
        
        avg_speed = self.speed_sum / self.speed_count if self.speed_count > 0 else 0
        print(f"Average Speed: {avg_speed:.2f} mph")
        
        session_duration = time.time() - self.session_start_time
        hours, remainder = divmod(int(session_duration), 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"Session Duration: {hours:02d}:{minutes:02d}:{seconds:02d}")
        
        sys.exit(0)  # Exit immediately
    
    def cleanup(self) -> None:
        """Clean up resources before exiting."""
        # Close ANT+ connections
        if self.fitness_equipment:
            try:
                self.fitness_equipment.close_channel()
                self.fitness_equipment = None
            except Exception as e:
                logger.error(f"Error closing fitness equipment channel: {e}")
        
        if self.node:
            try:
                self.node.stop()
                self.node = None
            except Exception as e:
                logger.error(f"Error stopping ANT+ node: {e}")
        
        # Update today's distance in the database if significant
        if self.db_connected and self.total_distance > 0.02:
            try:
                self.db.update_today_distance(self.device_id, self.total_distance)
            except Exception as e:
                logger.error(f"Error updating today's distance: {e}")
            
            # Close the database
            self.db.close()
    
    def initialize_ant(self) -> bool:
        """Initialize ANT+ node and fitness equipment device."""
        try:
            # Initialize ANT+ node
            print("Initializing ANT+ node...")
            self.node = Node()
            self.node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)
            
            # Set up Fitness Equipment device
            self.fitness_equipment = FitnessEquipment(self.node, device_id=self.device_id)
            self.fitness_equipment.on_device_data = self.on_fitness_equipment_data
            self.fitness_equipment.on_found = self.on_device_found
            
            # Start the node
            print("Starting ANT+ node...")
            self.node.start()
            return True
            
        except Exception as e:
            logger.error(f"Error initializing ANT+ node: {e}")
            self.cleanup()  # Clean up any partially initialized resources
            return False
    
    def attempt_reconnect(self) -> bool:
        """Attempt to reconnect to the ANT+ device."""
        self.connection_attempts += 1
        if self.connection_attempts > self.max_connection_attempts:
            logger.error(f"Maximum connection attempts ({self.max_connection_attempts}) reached. Giving up.")
            return False
        
        print(f"\nConnection attempt {self.connection_attempts}/{self.max_connection_attempts}...")
        
        # Clean up existing connections
        self.cleanup()
        
        # Wait before retrying
        time.sleep(self.reconnect_delay)
        
        # Try to initialize again
        return self.initialize_ant()
    
    def run(self) -> int:
        """Main function to display speed from ANT+ fitness equipment."""
        print("ANT+ Fitness Equipment Speed & Distance Display")
        print("----------------------------------------------")
        print(f"Looking for devices with ID: {self.device_id}")
        
        if self.db_connected:
            print(f"Database connected. Today's distance: {self.today_distance:.2f} miles, Yesterday's: {self.yesterday_distance:.2f} miles")
        else:
            print("Warning: Database not connected. Distance will not be saved.")
        
        try:
            # Initialize ANT+ node and equipment
            if not self.initialize_ant():
                if not self.attempt_reconnect():
                    return 1
            
            print("\nScanning for devices. Press Ctrl+C to stop.\n")
            
            # Keep the script running until exit_flag is set
            connection_check_interval = 10  # seconds
            last_connection_check = time.time()
            last_db_update_time = time.time()
            last_db_update_distance = 0.0
            
            while not self.exit_flag:
                time.sleep(0.1)  # Shorter sleep time for quicker response to Ctrl+C
                
                # Periodically check if we need to reconnect
                current_time = time.time()
                if current_time - last_connection_check > connection_check_interval:
                    last_connection_check = current_time
                    
                    # If we haven't received data for a while and we're not connected, try to reconnect
                    if (self.fitness_equipment and not self.fitness_equipment.connected and 
                        (self.last_update_time is None or current_time - self.last_update_time > connection_check_interval)):
                        print("\nConnection appears to be lost. Attempting to reconnect...")
                        if not self.attempt_reconnect():
                            print("Failed to reconnect after multiple attempts. Exiting.")
                            return 1
                
                # Periodically update the database if we've traveled more than 0.02 miles since last update
                if self.db_connected and (current_time - last_db_update_time > 60):  # Update at most once per minute
                    distance_since_last_update = self.total_distance - last_db_update_distance
                    if distance_since_last_update > 0.02:
                        if self.db.update_today_distance(self.device_id, distance_since_last_update):
                            # Update was successful
                            self.today_distance += distance_since_last_update
                            last_db_update_distance = self.total_distance
                            logger.debug(f"Updated database with {distance_since_last_update:.2f} miles")
                        last_db_update_time = current_time
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return 1
        finally:
            # Only clean up if not already done by signal handler
            if not self.exit_flag:
                self.cleanup()
                print("Done!")
        
        return 0


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Display speed data from ANT+ fitness equipment in large text.'
    )
    parser.add_argument(
        '-d', '--device-id', 
        type=int, 
        default=DEFAULT_DEVICE_ID,
        help=f'ANT+ device ID to connect to (default: {DEFAULT_DEVICE_ID})'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default=DEFAULT_DB_PATH,
        help=f'Path to SQLite database file (default: {DEFAULT_DB_PATH})'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Display distance statistics and exit'
    )
    return parser.parse_args()


def display_stats(db_path: str) -> None:
    """Display distance statistics from the database."""
    db = Database(db_path)
    if not db.connect():
        print("Error: Could not connect to database.")
        return
    
    stats = db.get_stats()
    if not stats:
        print("No distance data found.")
        return
    
    print("\nDistance Statistics")
    print("-----------------")
    for stat in stats:
        device_id, date, distance, last_updated = stat
        
        # Format the date nicely
        if date == datetime.now().date().isoformat():
            date_str = "Today"
        elif date == (datetime.now().date() - datetime.timedelta(days=1)).isoformat():
            date_str = "Yesterday"
        else:
            date_str = date
        
        # Format the last updated time
        if isinstance(last_updated, str):
            last_updated_dt = datetime.fromisoformat(last_updated)
        else:
            last_updated_dt = last_updated
        last_updated_str = last_updated_dt.strftime("%I:%M %p")
        
        print(f"Device ID: {device_id}")
        print(f"Date: {date_str}")
        print(f"Distance: {distance:.2f} miles")
        print(f"Last Updated: {last_updated_str}")
        print("-----------------")
    
    db.close()


def main():
    """Main entry point for the application."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # If stats flag is set, display stats and exit
    if args.stats:
        display_stats(args.db_path)
        return 0
    
    # Create and run the application
    app = SpeedDisplayApp(device_id=args.device_id, db_path=args.db_path)
    return app.run()


if __name__ == "__main__":
    sys.exit(main()) 