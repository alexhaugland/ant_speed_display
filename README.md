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
1. Search for ANT+ fitness equipment devices with ID 13500
2. Display the current speed in large text on the terminal
3. Update the display in real-time as speed changes

Press Ctrl+C to exit the program.

## Customization

You can modify the `TARGET_DEVICE_ID` variable in the script if your fitness equipment uses a different device ID. 