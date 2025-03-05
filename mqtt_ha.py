"""
MQTT and Home Assistant integration module for ANT+ Speed Display
Handles sending data to Home Assistant via MQTT with auto-discovery
"""

import logging
import time
from typing import Optional, Dict, Any, Callable

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Sensor, SensorInfo
from paho.mqtt.client import Client

# Configure logging
logger = logging.getLogger('mqtt_ha')

class MQTTHomeAssistant:
    """Class to handle MQTT and Home Assistant integration."""
    
    def __init__(self, mqtt_host: str, mqtt_port: int = 1883, 
                 mqtt_username: Optional[str] = None, mqtt_password: Optional[str] = None,
                 mqtt_client_id: str = "ant_speed_display", 
                 device_name: str = "ANT+ Speed Display",
                 device_id: int = 0):
        """Initialize MQTT and Home Assistant integration."""
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.mqtt_client_id = mqtt_client_id
        self.device_name = device_name
        self.device_id = device_id
        
        # MQTT client
        self.client: Optional[Client] = None
        
        # Sensors
        self.sensors: Dict[str, Sensor] = {}
        
        # Connection status
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to MQTT broker and set up Home Assistant entities."""
        try:
            # Create MQTT client
            self.client = Client(client_id=self.mqtt_client_id)
            
            # Set username and password if provided
            if self.mqtt_username and self.mqtt_password:
                self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            # Set up callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            # Connect to MQTT broker
            self.client.connect(self.mqtt_host, self.mqtt_port)
            
            # Start the MQTT loop in a background thread
            self.client.loop_start()
            
            # Wait for connection to be established
            timeout = 5  # seconds
            start_time = time.time()
            while not self.connected and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                logger.error("Failed to connect to MQTT broker within timeout period")
                return False
            
            # Create Home Assistant entities
            self._create_entities()
            
            return True
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            return False
    
    def _on_connect(self, client: Client, userdata: Any, flags: Dict, rc: int) -> None:
        """Callback when connected to MQTT broker."""
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
            self.connected = True
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
    
    def _on_disconnect(self, client: Client, userdata: Any, rc: int) -> None:
        """Callback when disconnected from MQTT broker."""
        logger.info(f"Disconnected from MQTT broker, return code: {rc}")
        self.connected = False
    
    def _create_entities(self) -> None:
        """Create Home Assistant entities."""
        # Base MQTT settings
        mqtt_settings = Settings.MQTT(
            host=self.mqtt_host,
            port=self.mqtt_port,
            username=self.mqtt_username,
            password=self.mqtt_password,
            client=self.client
        )
        
        # Device identifier
        device_id = f"ant_speed_display_{self.device_id}"
        
        # Create device configuration
        device = {
            "identifiers": [device_id],
            "name": self.device_name,
            "model": "ANT+ Speed Display",
            "manufacturer": "ANT+ Speed Display",
            "sw_version": "1.0"
        }
        
        # Create a base unique ID from the device name (lowercase, no spaces)
        base_unique_id = self.device_name.lower().replace(" ", "_")
        
        # Create speed sensor
        speed_info = SensorInfo(
            name="Current Speed",
            device_class="speed",
            unit_of_measurement="mph",
            state_class="measurement",
            device=device,
            unique_id=f"{base_unique_id}_speed"
        )
        speed_settings = Settings(mqtt=mqtt_settings, entity=speed_info)
        self.sensors["speed"] = Sensor(speed_settings)
        
        # Create today's total distance sensor
        today_distance_info = SensorInfo(
            name="Today's Distance",
            device_class="distance",
            unit_of_measurement="mi",
            state_class="total_increasing",
            device=device,
            unique_id=f"{base_unique_id}_today_distance"
        )
        today_distance_settings = Settings(mqtt=mqtt_settings, entity=today_distance_info)
        self.sensors["today_distance"] = Sensor(today_distance_settings)
        
        # Create yesterday's distance sensor
        yesterday_distance_info = SensorInfo(
            name="Yesterday's Distance",
            device_class="distance",
            unit_of_measurement="mi",
            state_class="total",
            device=device,
            unique_id=f"{base_unique_id}_yesterday_distance"
        )
        yesterday_distance_settings = Settings(mqtt=mqtt_settings, entity=yesterday_distance_info)
        self.sensors["yesterday_distance"] = Sensor(yesterday_distance_settings)
        
        # Create max speed sensor
        max_speed_info = SensorInfo(
            name="Max Speed",
            device_class="speed",
            unit_of_measurement="mph",
            state_class="measurement",
            device=device,
            unique_id=f"{base_unique_id}_max_speed"
        )
        max_speed_settings = Settings(mqtt=mqtt_settings, entity=max_speed_info)
        self.sensors["max_speed"] = Sensor(max_speed_settings)
        
        # Create average speed sensor
        avg_speed_info = SensorInfo(
            name="Average Speed",
            device_class="speed",
            unit_of_measurement="mph",
            state_class="measurement",
            device=device,
            unique_id=f"{base_unique_id}_avg_speed"
        )
        avg_speed_settings = Settings(mqtt=mqtt_settings, entity=avg_speed_info)
        self.sensors["avg_speed"] = Sensor(avg_speed_settings)
    
    def update_speed(self, speed: float) -> None:
        """Update the speed sensor."""
        if self.connected and "speed" in self.sensors:
            self.sensors["speed"].set_state(f"{speed:.2f}")
    
    def update_today_distance(self, distance: float) -> None:
        """Update today's total distance sensor."""
        if self.connected and "today_distance" in self.sensors:
            self.sensors["today_distance"].set_state(f"{distance:.2f}")
    
    def update_yesterday_distance(self, distance: float) -> None:
        """Update yesterday's distance sensor."""
        if self.connected and "yesterday_distance" in self.sensors:
            self.sensors["yesterday_distance"].set_state(f"{distance:.2f}")
    
    def update_max_speed(self, speed: float) -> None:
        """Update the max speed sensor."""
        if self.connected and "max_speed" in self.sensors:
            self.sensors["max_speed"].set_state(f"{speed:.2f}")
    
    def update_avg_speed(self, speed: float) -> None:
        """Update the average speed sensor."""
        if self.connected and "avg_speed" in self.sensors:
            self.sensors["avg_speed"].set_state(f"{speed:.2f}")
    
    def update_all(self, speed: float, today_distance: float,
                  yesterday_distance: float, max_speed: float, avg_speed: float) -> None:
        """Update all sensors at once."""
        self.update_speed(speed)
        self.update_today_distance(today_distance)
        self.update_yesterday_distance(yesterday_distance)
        self.update_max_speed(max_speed)
        self.update_avg_speed(avg_speed)
    
    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self.client and self.connected:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                logger.info("Disconnected from MQTT broker")
            except Exception as e:
                logger.error(f"Error disconnecting from MQTT broker: {e}")
            finally:
                self.connected = False 