#!./venv/bin/python3
"""
ANT+ Speed Display for Fitness Equipment
Displays speed data and distance traveled from ANT+ fitness equipment in large text on the terminal
and/or sends data to Home Assistant via MQTT
Specifically looks for devices with ID 13500 by default
Uses imperial units (mph and miles)
"""

import sys
import time
import os
import signal
import sqlite3
from datetime import datetime, date, timedelta
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

# Import our modules
from terminal_display import TerminalDisplay
from mqtt_ha import MQTTHomeAssistant
from config import load_config, Config

# Configure logging
logging.basicConfig(level=logging.WARN, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ant_scanner')

# Conversion constants
KM_TO_MILES = 0.621371  # Conversion factor from kilometers to miles
MS_TO_KMH = 3.6  # Conversion factor from m/s to km/h

# Database constants
DEFAULT_DB_PATH = "~/.ant_speed_display.db"
DB_TABLE_NAME = "daily_distance"


class Database:
    """Database manager for storing daily distance data."""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize the database connection."""
        self.db_path = os.path.expanduser(db_path)
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
            yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
            
            # Delete all records except today and yesterday
            self.cursor.execute(
                f"DELETE FROM {DB_TABLE_NAME} WHERE date != ? AND date != ?",
                (today, yesterday)
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def get_distance_for_date(self, device_id: int, target_date: date) -> float:
        """Get the total distance for a specific date with this device."""
        try:
            date_str = target_date.isoformat()
            self.cursor.execute(
                f"SELECT distance FROM {DB_TABLE_NAME} WHERE date = ? AND device_id = ?",
                (date_str, device_id)
            )
            result = self.cursor.fetchone()
            return result[0] if result else 0.0
        except Exception as e:
            logger.error(f"Error getting distance for {target_date.isoformat()}: {e}")
            return 0.0
    
    def update_distance_for_date(self, device_id: int, target_date: date, distance: float) -> bool:
        """Update distance for a specific date if the new distance is significant (> 0.02 miles)."""
        if distance <= 0.02:
            logger.debug(f"Distance {distance} is too small to record (≤ 0.02 miles)")
            return False
            
        try:
            date_str = target_date.isoformat()
            now = datetime.now()
            
            # Check if we already have a record for this date
            self.cursor.execute(
                f"SELECT distance FROM {DB_TABLE_NAME} WHERE date = ? AND device_id = ?",
                (date_str, device_id)
            )
            result = self.cursor.fetchone()
            
            if result:
                # Update existing record
                self.cursor.execute(
                    f"UPDATE {DB_TABLE_NAME} SET distance = distance + ?, last_updated = ? WHERE date = ? AND device_id = ?",
                    (distance, now, date_str, device_id)
                )
            else:
                # Insert new record
                self.cursor.execute(
                    f"INSERT INTO {DB_TABLE_NAME} (date, device_id, distance, last_updated) VALUES (?, ?, ?, ?)",
                    (date_str, device_id, distance, now)
                )
            
            self.conn.commit()
            
            # Clean up old data
            self._cleanup_old_data()
            return True
        except Exception as e:
            logger.error(f"Error updating distance for {target_date.isoformat()}: {e}")
            return False
    
    def get_stats(self) -> List[Tuple]:
        """Get statistics for today and yesterday."""
        try:
            today = datetime.now().date().isoformat()
            yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
            
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


class Statistics:
    """Class to track and calculate workout statistics."""
    
    def __init__(self, device_id: int, db: Optional[Database] = None):
        """Initialize statistics tracking."""
        self.device_id = device_id
        self.db = db
        self.db_connected = db is not None
        
        # Current session stats
        self.session_distance = 0.0
        self.session_start_time = time.time()
        self.current_speed = 0.0
        self.max_speed = 0.0
        
        # 5-minute rolling average for speed (300 seconds)
        self.speed_history = []  # List of (timestamp, speed) tuples
        self.ROLLING_AVG_WINDOW = 300  # 5 minutes in seconds
        
        # Date tracking
        self.current_date = datetime.now().date()
        
        # Daily distance tracking
        self.today_distance = 0.0
        self.yesterday_distance = 0.0
        
        # Load initial values from database
        self._load_daily_distances()
    
    def _load_daily_distances(self) -> None:
        """Load today's and yesterday's distances from the database."""
        if not self.db_connected:
            return
            
        try:
            self.today_distance = self.db.get_distance_for_date(self.device_id, self.current_date)
            yesterday = self.current_date - timedelta(days=1)
            self.yesterday_distance = self.db.get_distance_for_date(self.device_id, yesterday)
        except Exception as e:
            logger.error(f"Error loading daily distances: {e}")
    
    def _check_date_change(self) -> bool:
        """Check if the date has changed and update tracking if needed.
        
        Returns:
            bool: True if the date changed, False otherwise
        """
        current_date = datetime.now().date()
        
        # Check if the date has changed
        if current_date != self.current_date:
            logger.info(f"Date changed from {self.current_date.isoformat()} to {current_date.isoformat()}")
            
            # Save any accumulated distance to the old date before resetting
            if self.db_connected and self.session_distance > 0.02:
                try:
                    self.db.update_distance_for_date(self.device_id, self.current_date, self.session_distance)
                    logger.info(f"Saved {self.session_distance:.2f} miles to {self.current_date.isoformat()}")
                except Exception as e:
                    logger.error(f"Error saving distance before date change: {e}")
            
            # Yesterday is now what was today
            self.yesterday_distance = self.today_distance
            
            # Update the current date
            self.current_date = current_date
            
            # Reset today's distance to 0 since it's a new day
            self.today_distance = 0.0
            
            # Also reload from DB in case there were previous runs today
            if self.db_connected:
                try:
                    self.today_distance = self.db.get_distance_for_date(self.device_id, self.current_date)
                except Exception as e:
                    logger.error(f"Error loading today's distance after date change: {e}")
            
            # Reset session distance since we're starting a new day
            self.session_distance = 0.0
            
            return True
        
        return False
    
    def update_speed(self, speed_mph: float) -> None:
        """Update speed statistics."""
        # Check for date change first
        self._check_date_change()
        
        self.current_speed = speed_mph
        
        # Update max speed
        if speed_mph > self.max_speed:
            self.max_speed = speed_mph
        
        # Update rolling average speed calculation
        current_time = time.time()
        self.speed_history.append((current_time, speed_mph))
        
        # Remove entries older than the rolling window
        cutoff_time = current_time - self.ROLLING_AVG_WINDOW
        self.speed_history = [entry for entry in self.speed_history if entry[0] >= cutoff_time]
    
    def add_distance(self, distance_miles: float) -> None:
        """Add distance to the current session."""
        # Check for date change first
        self._check_date_change()
        
        self.session_distance += distance_miles
    
    def save_to_database(self) -> bool:
        """Save current session distance to the database if significant."""
        # Check for date change first
        self._check_date_change()
        
        if not self.db_connected or self.session_distance <= 0.02:
            return False
            
        try:
            result = self.db.update_distance_for_date(self.device_id, self.current_date, self.session_distance)
            if result:
                # Update was successful, update today's distance
                self.today_distance += self.session_distance
                # Reset session distance since it's been saved
                self.session_distance = 0.0
            return result
        except Exception as e:
            logger.error(f"Error saving statistics to database: {e}")
            return False
    
    def get_avg_speed(self) -> float:
        """Get the average speed over the last 5 minutes."""
        if not self.speed_history:
            return 0.0
        
        # Calculate average of all speeds in the history
        total_speed = sum(speed for _, speed in self.speed_history)
        return total_speed / len(self.speed_history) if self.speed_history else 0.0
    
    def get_session_duration(self) -> int:
        """Get the session duration in seconds."""
        return int(time.time() - self.session_start_time)
    
    def get_formatted_session_duration(self) -> str:
        """Get the formatted session duration as HH:MM:SS."""
        duration = self.get_session_duration()
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def get_total_today_distance(self) -> float:
        """Get the total distance for today including the current session."""
        # Check for date change first
        self._check_date_change()
        
        return self.today_distance + self.session_distance


class SpeedDisplayApp:
    """Main application class for ANT+ Speed Display."""
    
    def __init__(self, config: Config):
        """Initialize the application with the specified configuration."""
        self.config = config
        self.device_id = config.device_id
        self.node: Optional[Node] = None
        self.fitness_equipment: Optional[FitnessEquipment] = None
        self.exit_flag = False
        self.last_update_time: Optional[float] = None  # Last time we received speed data
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.reconnect_delay = 2  # seconds
        
        # Database setup
        self.db = Database(config.db_path)
        self.db_connected = self.db.connect()
        
        # Statistics tracking
        self.stats = Statistics(self.device_id, self.db if self.db_connected else None)
        
        # Terminal display setup
        self.terminal_display = None
        if config.use_terminal_display:
            self.terminal_display = TerminalDisplay()
        
        # MQTT and Home Assistant setup
        self.mqtt_ha = None
        if config.use_mqtt and config.mqtt_host:
            self.mqtt_ha = MQTTHomeAssistant(
                mqtt_host=config.mqtt_host,
                mqtt_port=config.mqtt_port,
                mqtt_username=config.mqtt_username,
                mqtt_password=config.mqtt_password,
                mqtt_client_id=config.mqtt_client_id,
                device_name=config.device_name,
                device_id=self.device_id
            )
            self.mqtt_connected = self.mqtt_ha.connect()
        else:
            self.mqtt_connected = False
        
        # Set up signal handler for clean exit
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def update_display(self) -> None:
        """Update the terminal display and/or MQTT with current speed and distance."""
        try:
            # Format speed to 2 decimal places
            speed_text = f"{self.stats.current_speed:.2f}"
            
            # Format distance to 2 decimal places
            distance_text = f"{self.stats.session_distance:.2f}"
            
            # Update terminal display if enabled
            if self.terminal_display:
                self.terminal_display.display_big_text(
                    speed_text, 
                    distance_text, 
                    self.stats.get_total_today_distance(),
                    self.stats.yesterday_distance
                )
            
            # Update MQTT if connected
            if self.mqtt_connected:
                self.mqtt_ha.update_all(
                    self.stats.current_speed,
                    self.stats.get_total_today_distance(),
                    self.stats.yesterday_distance,
                    self.stats.max_speed,
                    self.stats.get_avg_speed()
                )
        except Exception as e:
            logger.error(f"Error updating display: {e}")
    
    def on_fitness_equipment_data(self, page: int, page_name: str, data: FitnessEquipmentData) -> None:
        """Callback for receiving fitness equipment data."""
        try:
            # Only process data if it's from the general_fe page (page 16)
            if page_name == "general_fe":
                # Get current time
                current_time = time.time()
                
                # Convert speed from m/s to mph
                # First convert to km/h (multiply by 3.6), then to mph (multiply by KM_TO_MILES)
                speed_mph = data.speed * MS_TO_KMH * KM_TO_MILES
                
                # Update speed statistics
                self.stats.update_speed(speed_mph)
                
                # Calculate distance if we have a previous update
                if self.last_update_time is not None:
                    elapsed_seconds = current_time - self.last_update_time
                    distance = self.calculate_distance(speed_mph, elapsed_seconds)
                    self.stats.add_distance(distance)
                
                # Update last update time
                self.last_update_time = current_time
                
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
        if self.terminal_display:
            self.terminal_display.display_final_stats(
                self.stats.session_distance,
                self.stats.get_total_today_distance(),
                self.stats.yesterday_distance,
                self.stats.current_speed,
                self.stats.max_speed,
                self.stats.get_avg_speed(),
                self.stats.get_formatted_session_duration()
            )
        
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
        
        # Save final statistics to database
        if self.db_connected:
            try:
                self.stats.save_to_database()
            except Exception as e:
                logger.error(f"Error saving final statistics: {e}")
            
            # Close the database
            self.db.close()
        
        # Disconnect from MQTT
        if self.mqtt_connected:
            try:
                self.mqtt_ha.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from MQTT: {e}")
    
    def calculate_distance(self, speed_mph: float, elapsed_seconds: float) -> float:
        """Calculate distance traveled based on speed and time."""
        # Convert mph to miles/second, then multiply by elapsed seconds
        return (speed_mph / 3600.0) * elapsed_seconds
    
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
            print(f"Database connected. Today's distance: {self.stats.today_distance:.2f} miles, Yesterday's: {self.stats.yesterday_distance:.2f} miles")
        else:
            print("Warning: Database not connected. Distance will not be saved.")
        
        if self.terminal_display:
            print("Terminal display enabled.")
        else:
            print("Terminal display disabled.")
        
        if self.mqtt_connected:
            print(f"MQTT connected to {self.config.mqtt_host}. Data will be sent to Home Assistant.")
        else:
            if self.config.use_mqtt:
                print(f"Warning: MQTT connection failed. Data will not be sent to Home Assistant.")
            else:
                print("MQTT disabled. Data will not be sent to Home Assistant.")
        
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
            db_update_interval = 60  # Update database every minute
            
            while not self.exit_flag:
                time.sleep(0.1)  # Shorter sleep time for quicker response to Ctrl+C
                
                current_time = time.time()
                
                # Periodically check if we need to reconnect
                if current_time - last_connection_check > connection_check_interval:
                    last_connection_check = current_time
                    
                    # If we haven't received data for a while and we're not connected, try to reconnect
                    if (self.fitness_equipment and not self.fitness_equipment.connected and 
                        (self.last_update_time is None or current_time - self.last_update_time > connection_check_interval)):
                        print("\nConnection appears to be lost. Attempting to reconnect...")
                        if not self.attempt_reconnect():
                            print("Failed to reconnect after multiple attempts. Exiting.")
                            return 1
                
                # Periodically update the database
                if self.db_connected and (current_time - last_db_update_time > db_update_interval):
                    if self.stats.save_to_database():
                        logger.debug(f"Updated database with session distance")
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
        elif date == (datetime.now().date() - timedelta(days=1)).isoformat():
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
    # Load configuration
    config = load_config()
    
    # Set logging level based on verbose flag
    if config.verbose:
        logger.setLevel(logging.DEBUG)
    
    # If stats flag is set, display stats and exit
    if config.stats_only:
        display_stats(config.db_path)
        return 0
    
    # Create and run the application
    app = SpeedDisplayApp(config)
    return app.run()


if __name__ == "__main__":
    sys.exit(main()) 