# ANT+ Speed Display

A Python utility that displays speed data and distance traveled from ANT+ fitness equipment in large text on the terminal. Perfect for monitoring your workout metrics from a distance. Uses imperial units (mph and miles).

## Requirements

- Python 3.6+
- ANT+ USB receiver/dongle
- ANT+ compatible fitness equipment (treadmill, bike trainer, etc.)
- `openant` library

## Setup

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up USB permissions (Linux only):
   ```
   sudo python install_rules.py
   ```

## Usage

Connect your ANT+ USB receiver and run: 
```
./speed_display.py
```

The script will:
1. Search for ANT+ fitness equipment devices with ID 13500 (default)
2. Display both current speed and total distance in large text on the terminal
3. Show units (mph and mi) in small text next to the values
4. Calculate and track distance traveled based on speed data
5. Update the display in real-time as metrics change

### Display Format

The display is organized into two sections:
- **Speed**: Shows current speed in mph at the top
- **Distance**: Shows total distance traveled in miles at the bottom

Both metrics are displayed simultaneously in large ASCII art with their respective units shown in small text.

### Keyboard Controls

- **Ctrl+C**: Exit the program and display final stats

### Command-line Options

You can specify a different device ID using the command-line:

```
./speed_display.py --device-id 12345
```

Available options:

```
./speed_display.py --help
```

## Final Stats

When you exit the program using Ctrl+C, it will display final statistics:
- Total distance traveled (miles)
- Last recorded speed (mph)

## Customization

You can modify the appearance of the display by editing the `BIG_NUMBERS` dictionary in the script. 