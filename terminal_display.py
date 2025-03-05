"""
Terminal display module for ANT+ Speed Display
Handles displaying speed and distance data in large text on the terminal
"""

import os
import logging

# Configure logging
logger = logging.getLogger('terminal_display')

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


class TerminalDisplay:
    """Class to handle displaying data in large text on the terminal."""
    
    def __init__(self):
        """Initialize the terminal display."""
        pass
    
    def display_big_text(self, speed_text: str, distance_text: str, 
                         today_distance: float, yesterday_distance: float) -> None:
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
                print(f"{line}  mi / {today_distance:.2f} mi / {yesterday_distance:.2f} mi")
            else:
                print(line)
        
        print("\n")  # Add some space at the bottom
    
    def display_final_stats(self, session_distance: float, total_today_distance: float,
                           yesterday_distance: float, current_speed: float, max_speed: float,
                           avg_speed: float, session_duration: str) -> None:
        """Display final statistics when exiting."""
        print(f"\nFinal Stats:")
        print(f"Session Distance: {session_distance:.2f} miles")
        print(f"Today's Total Distance: {total_today_distance:.2f} miles")
        print(f"Yesterday's Distance: {yesterday_distance:.2f} miles")
        print(f"Last Speed: {current_speed:.2f} mph")
        print(f"Max Speed: {max_speed:.2f} mph")
        print(f"Average Speed (last 5 min): {avg_speed:.2f} mph")
        print(f"Session Duration: {session_duration}") 