# ANT+ Speed Display

A Python utility that displays speed data and distance traveled from ANT+ fitness equipment in large text on the terminal and/or sends data to Home Assistant via MQTT. Perfect for monitoring your workout metrics from a distance. Uses imperial units (mph and miles). Designed to run continuously in the background.

## Requirements

- Python 3.6+
- ANT+ USB receiver/dongle
- ANT+ compatible fitness equipment (treadmill, bike trainer, etc.)
- `openant` library
- For Home Assistant integration:
  - MQTT broker
  - Home Assistant with MQTT integration enabled
  - `ha-mqtt-discoverable` library
  - `paho-mqtt` library

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
2. Display both current speed and total distance in large text on the terminal (if enabled)
3. Send data to Home Assistant via MQTT (if configured)
4. Show units (mph and mi) in small text next to the values
5. Calculate and track distance traveled based on speed data
6. Update the display in real-time as metrics change

### Display Format

The terminal display is organized into two sections:
- **Speed**: Shows current speed in mph at the top
- **Distance**: Shows total distance traveled in miles at the bottom

Both metrics are displayed simultaneously in large ASCII art with their respective units shown in small text.

### Home Assistant Integration

When MQTT is configured, the following entities will be automatically created in Home Assistant:
- Current Speed (mph)
- Today's Distance (miles)
- Yesterday's Distance (miles)
- Max Speed (mph)
- Average Speed (mph) - calculated over the last 5 minutes

These entities will be automatically discovered by Home Assistant using the MQTT discovery protocol.

### Running in the Background

This application is designed to run continuously in the background. You can use systemd, screen, or tmux to keep it running:

#### Using systemd (recommended for Linux systems):

A sample systemd service file is included in the repository (`ant-speed-display.service`). You can customize it for your environment and install it with:

```
sudo cp ant-speed-display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ant-speed-display.service
sudo systemctl start ant-speed-display.service
```

You may need to edit the file to match your username, paths, and MQTT settings before installing it.

### Configuration

You can configure the application using command line arguments or a configuration file.

#### Command Line Options

```
./speed_display.py --help
```

Available options:

```
  -h, --help            show this help message and exit
  -d DEVICE_ID, --device-id DEVICE_ID
                        ANT+ device ID to connect to (default: 13500)
  --db-path DB_PATH     Path to SQLite database file (default: ~/.ant_speed_display.db)
  --no-terminal         Disable terminal display
  --mqtt-host MQTT_HOST
                        MQTT broker hostname or IP address
  --mqtt-port MQTT_PORT
                        MQTT broker port (default: 1883)
  --mqtt-username MQTT_USERNAME
                        MQTT broker username
  --mqtt-password MQTT_PASSWORD
                        MQTT broker password
  --mqtt-client-id MQTT_CLIENT_ID
                        MQTT client ID (default: ant_speed_display)
  --device-name DEVICE_NAME
                        Device name for Home Assistant (default: ANT+ Speed Display)
  -c CONFIG, --config CONFIG
                        Path to config file (default: ~/.ant_speed_display.conf)
  -v, --verbose         Enable verbose logging
  --stats               Display distance statistics and exit
```

#### Configuration File

You can create a configuration file at `~/.ant_speed_display.conf` or specify a custom path with the `--config` option. A sample configuration file is provided in `sample_config.conf`.

Example:
```ini
[ANT]
device_id = 13500

[Database]
db_path = ~/.ant_speed_display.db

[Display]
use_terminal_display = true

[MQTT]
mqtt_host = 192.168.1.100
mqtt_port = 1883
mqtt_username = username
mqtt_password = password
mqtt_client_id = ant_speed_display
device_name = ANT+ Speed Display
```

### Keyboard Controls

- **Ctrl+C**: Exit the program and display final stats

## Final Stats

When you exit the program using Ctrl+C, it will display final statistics:
- Total distance traveled (miles)
- Today's total distance (miles)
- Yesterday's distance (miles)
- Last recorded speed (mph)
- Max speed (mph)
- Average speed (mph)
- Session duration (HH:MM:SS)

## Customization

You can modify the appearance of the terminal display by editing the `BIG_NUMBERS` dictionary in the `terminal_display.py` file. 