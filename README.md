# ANT+ Speed Display

A Python utility that displays speed data from ANT+ fitness equipment in large text on the terminal. Perfect for monitoring your workout speed from a distance.

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
2. Display the current speed in large text on the terminal
3. Update the display in real-time as speed changes

Press Ctrl+C to exit the program.

### Command-line Options

You can specify a different device ID using the command-line:

```
./speed_display.py --device-id 12345
```

Or using the short form:

```
./speed_display.py -d 12345
```

To see all available options:

```
./speed_display.py --help
```

## Customization

You can modify the appearance of the display by editing the `BIG_NUMBERS` dictionary in the script. 