#!./venv/bin/python3
"""
ANT+ Device Scanner
Scans for ANT+ devices using a connected USB receiver.
"""

import sys
import time
from datetime import datetime
import logging

try:
    from openant.easy.node import Node
    from openant.devices import scanner
    from openant.base.commons import format_list
except ImportError:
    print("Error: Required libraries not found.")
    print("Please install the required packages with: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ant_scanner')

def main():
    """Main function to scan for ANT+ devices."""
    print("ANT+ Device Scanner")
    print("-------------------")
    
    try:
        # Initialize ANT+ node
        print("Initializing ANT+ node...")
        node = Node()
        
        # Connect to USB stick
        print("Connecting to ANT+ USB receiver...")
        node.start()
        
        # Create a scanner
        print("Starting device scan...")
        scan = scanner.Scanner(node)
        
        # Start scanning
        scan.start()
        
        print("\nScanning for ANT+ devices. Press Ctrl+C to stop.\n")
        print("Time\t\t\tDevice Type\t\tDevice Number\tTransmission Type")
        print("-" * 80)
        
        # Keep scanning until user interrupts
        try:
            while True:
                for device in scan.devices.values():
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    device_type = device.device_type
                    device_number = device.device_number
                    trans_type = device.transmission_type
                    
                    print(f"{timestamp}\t{device_type}\t\t{device_number}\t\t{trans_type}")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nScan interrupted by user.")
        
        # Stop scanning and close connection
        scan.stop()
        node.stop()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 