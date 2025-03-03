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

# Global variables
node = None
fitness_equipment = None
exit_flag = False
total_distance = 0.0  # Total distance in miles
last_update_time = None  # Last time we received speed data
current_speed = 0.0  # Current speed in mph

# Default target device ID
DEFAULT_DEVICE_ID = 13500

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

# Conversion constants
KM_TO_MILES = 0.621371  # Conversion factor from kilometers to miles

def display_big_text(speed_text, distance_text):
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

def calculate_distance(speed_mph, elapsed_seconds):
    """Calculate distance traveled based on speed and time."""
    # Convert mph to miles/second, then multiply by elapsed seconds
    return (speed_mph / 3600.0) * elapsed_seconds

def update_display():
    """Update the terminal display with current speed and distance."""
    # Format speed to 2 decimal places
    speed_text = f"{current_speed:.2f}"
    
    # Format distance to 2 decimal places
    distance_text = f"{total_distance:.2f}"
    
    # Display both speed and distance
    display_big_text(speed_text, distance_text)

def on_fitness_equipment_data(page: int, page_name: str, data: FitnessEquipmentData):
    """Callback for receiving fitness equipment data."""
    global last_update_time, total_distance, current_speed
    
    # Only process data if it's from the general_fe page (page 16)
    if page_name == "general_fe":
        # Get current time
        current_time = time.time()
        
        # Convert speed from m/s to mph
        # First convert to km/h (multiply by 3.6), then to mph (multiply by KM_TO_MILES)
        current_speed = data.speed * 3.6 * KM_TO_MILES
        
        # Calculate distance if we have a previous update
        if last_update_time is not None:
            elapsed_seconds = current_time - last_update_time
            distance = calculate_distance(current_speed, elapsed_seconds)
            total_distance += distance
        
        # Update last update time
        last_update_time = current_time
        
        # Update display
        update_display()

def on_device_found(device):
    """Callback when a device is found."""
    print(f"\nDevice found: {device.name} (ID: {device.device_id})")
    print("Waiting for speed data...")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global exit_flag
    exit_flag = True
    print("\nExiting...", end="", flush=True)
    cleanup()
    print(" Done!")
    
    # Show final stats
    print(f"\nFinal Stats:")
    print(f"Total Distance: {total_distance:.2f} miles")
    print(f"Last Speed: {current_speed:.2f} mph")
    
    sys.exit(0)  # Exit immediately

def cleanup():
    """Clean up resources before exiting."""
    global node, fitness_equipment
    
    if fitness_equipment:
        try:
            fitness_equipment.close_channel()
            fitness_equipment = None
        except:
            pass
    
    if node:
        try:
            node.stop()
            node = None
        except:
            pass

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
    return parser.parse_args()

def main():
    """Main function to display speed from ANT+ fitness equipment."""
    global node, fitness_equipment
    
    # Parse command line arguments
    args = parse_arguments()
    device_id = args.device_id
    
    # Set up signal handler for clean exit
    signal.signal(signal.SIGINT, signal_handler)
    
    print("ANT+ Fitness Equipment Speed & Distance Display")
    print("----------------------------------------------")
    print(f"Looking for devices with ID: {device_id}")
    
    try:
        # Initialize ANT+ node
        print("Initializing ANT+ node...")
        node = Node()
        node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)
        
        # Set up Fitness Equipment device
        fitness_equipment = FitnessEquipment(node, device_id=device_id)
        fitness_equipment.on_device_data = on_fitness_equipment_data
        fitness_equipment.on_found = lambda: on_device_found(fitness_equipment)
        
        # Start the node
        print("Starting ANT+ node...")
        node.start()
        
        print("\nScanning for devices. Press Ctrl+C to stop.\n")
        
        # Keep the script running until exit_flag is set
        while not exit_flag:
            time.sleep(0.1)  # Shorter sleep time for quicker response to Ctrl+C
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        # Only clean up if not already done by signal handler
        if not exit_flag:
            cleanup()
            print("Done!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 