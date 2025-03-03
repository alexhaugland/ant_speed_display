#!./venv/bin/python3
"""
ANT+ Device Scanner for Fitness Equipment
Specifically looks for devices with ID 13500 and displays speed in big text
"""

import sys
import time
import os
import signal
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

# Target device ID
TARGET_DEVICE_ID = 13500

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

# Global variables
node = None
fitness_equipment = None
exit_flag = False

def display_big_text(text):
    """Display text in big ASCII art."""
    # Clear the terminal
    os.system('clear' if os.name == 'posix' else 'cls')
    
    # Convert text to big ASCII art
    lines = [""] * 7
    for char in text:
        if char in BIG_NUMBERS:
            for i in range(7):
                lines[i] += BIG_NUMBERS[char][i] + " "
        else:
            # For characters not in our dictionary, use space
            for i in range(7):
                lines[i] += BIG_NUMBERS[' '][i] + " "
    
    # Print the big text
    print("\n" * 3)  # Add some space at the top
    for line in lines:
        print(line)
    print("\n" * 3)  # Add some space at the bottom

def on_fitness_equipment_data(page: int, page_name: str, data: FitnessEquipmentData):
    """Callback for receiving fitness equipment data."""
    # Only process data if it's from the general_fe page (page 16)
    if page_name == "general_fe":
        # Convert speed from m/s to km/h
        speed_kmh = data.speed * 3.6
        
        # Format speed to 2 decimal places
        speed_text = f"{speed_kmh:.2f}"
        
        # Display speed in big text
        display_big_text(speed_text)

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

def main():
    """Main function to scan for specific ANT+ devices."""
    global node, fitness_equipment
    
    # Set up signal handler for clean exit
    signal.signal(signal.SIGINT, signal_handler)
    
    print("ANT+ Fitness Equipment Speed Display")
    print("------------------------------------")
    print(f"Looking for devices with ID: {TARGET_DEVICE_ID}")
    
    try:
        # Initialize ANT+ node
        print("Initializing ANT+ node...")
        node = Node()
        node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)
        
        # Set up Fitness Equipment device
        fitness_equipment = FitnessEquipment(node, device_id=TARGET_DEVICE_ID)
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