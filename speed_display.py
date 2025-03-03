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
from datetime import datetime
import logging
from typing import Optional, Dict, List, Callable, Any

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


class SpeedDisplayApp:
    """Main application class for ANT+ Speed Display."""
    
    def __init__(self, device_id: int = DEFAULT_DEVICE_ID):
        """Initialize the application with the specified device ID."""
        self.device_id = device_id
        self.node: Optional[Node] = None
        self.fitness_equipment: Optional[FitnessEquipment] = None
        self.exit_flag = False
        self.total_distance = 0.0  # Total distance in miles
        self.last_update_time: Optional[float] = None  # Last time we received speed data
        self.current_speed = 0.0  # Current speed in mph
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.reconnect_delay = 2  # seconds
        
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
        print("DISTANCE:")
        
        # Print distance with units
        for i, line in enumerate(distance_lines):
            if i == 3:  # Middle line, add units
                print(f"{line}  mi")
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
        print(f"Total Distance: {self.total_distance:.2f} miles")
        print(f"Last Speed: {self.current_speed:.2f} mph")
        
        sys.exit(0)  # Exit immediately
    
    def cleanup(self) -> None:
        """Clean up resources before exiting."""
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
        
        try:
            # Initialize ANT+ node and equipment
            if not self.initialize_ant():
                if not self.attempt_reconnect():
                    return 1
            
            print("\nScanning for devices. Press Ctrl+C to stop.\n")
            
            # Keep the script running until exit_flag is set
            connection_check_interval = 10  # seconds
            last_connection_check = time.time()
            
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
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create and run the application
    app = SpeedDisplayApp(device_id=args.device_id)
    return app.run()


if __name__ == "__main__":
    sys.exit(main()) 