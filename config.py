"""
Configuration module for ANT+ Speed Display
Handles loading configuration from command line arguments or a config file
"""

import os
import argparse
import configparser
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger('config')

# Default values
DEFAULT_DEVICE_ID = 13500
DEFAULT_DB_PATH = os.path.expanduser("~/.ant_speed_display.db")
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.ant_speed_display.conf")

class Config:
    """Class to handle configuration from command line arguments or a config file."""
    
    def __init__(self):
        """Initialize configuration with default values."""
        # ANT+ settings
        self.device_id = DEFAULT_DEVICE_ID
        
        # Database settings
        self.db_path = DEFAULT_DB_PATH
        
        # Display settings
        self.use_terminal_display = True
        
        # MQTT settings
        self.use_mqtt = False
        self.mqtt_host = None
        self.mqtt_port = 1883
        self.mqtt_username = None
        self.mqtt_password = None
        self.mqtt_client_id = "ant_speed_display"
        self.device_name = "ANT+ Speed Display"
        
        # Other settings
        self.verbose = False
        self.stats_only = False
    
    def load_from_args(self, args: argparse.Namespace) -> None:
        """Load configuration from command line arguments."""
        # ANT+ settings
        if hasattr(args, 'device_id') and args.device_id is not None:
            self.device_id = args.device_id
        
        # Database settings
        if hasattr(args, 'db_path') and args.db_path is not None:
            self.db_path = args.db_path
        
        # Display settings
        if hasattr(args, 'no_terminal') and args.no_terminal is not None:
            self.use_terminal_display = not args.no_terminal
        
        # MQTT settings
        if hasattr(args, 'mqtt_host') and args.mqtt_host is not None:
            self.use_mqtt = True
            self.mqtt_host = args.mqtt_host
        
        if hasattr(args, 'mqtt_port') and args.mqtt_port is not None:
            self.mqtt_port = args.mqtt_port
        
        if hasattr(args, 'mqtt_username') and args.mqtt_username is not None:
            self.mqtt_username = args.mqtt_username
        
        if hasattr(args, 'mqtt_password') and args.mqtt_password is not None:
            self.mqtt_password = args.mqtt_password
        
        if hasattr(args, 'mqtt_client_id') and args.mqtt_client_id is not None:
            self.mqtt_client_id = args.mqtt_client_id
        
        if hasattr(args, 'device_name') and args.device_name is not None:
            self.device_name = args.device_name
        
        # Other settings
        if hasattr(args, 'verbose') and args.verbose is not None:
            self.verbose = args.verbose
        
        if hasattr(args, 'stats') and args.stats is not None:
            self.stats_only = args.stats
        
        # Config file
        if hasattr(args, 'config') and args.config is not None:
            self.load_from_file(args.config)
    
    def load_from_file(self, config_path: str = DEFAULT_CONFIG_PATH) -> None:
        """Load configuration from a config file."""
        if not os.path.exists(config_path):
            logger.debug(f"Config file {config_path} not found, using defaults")
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(config_path)
            
            # ANT+ settings
            if 'ANT' in config:
                if 'device_id' in config['ANT']:
                    self.device_id = config['ANT'].getint('device_id')
            
            # Database settings
            if 'Database' in config:
                if 'db_path' in config['Database']:
                    self.db_path = config['Database']['db_path']
            
            # Display settings
            if 'Display' in config:
                if 'use_terminal_display' in config['Display']:
                    self.use_terminal_display = config['Display'].getboolean('use_terminal_display')
            
            # MQTT settings
            if 'MQTT' in config:
                if 'mqtt_host' in config['MQTT']:
                    self.use_mqtt = True
                    self.mqtt_host = config['MQTT']['mqtt_host']
                
                if 'mqtt_port' in config['MQTT']:
                    self.mqtt_port = config['MQTT'].getint('mqtt_port')
                
                if 'mqtt_username' in config['MQTT']:
                    self.mqtt_username = config['MQTT']['mqtt_username']
                
                if 'mqtt_password' in config['MQTT']:
                    self.mqtt_password = config['MQTT']['mqtt_password']
                
                if 'mqtt_client_id' in config['MQTT']:
                    self.mqtt_client_id = config['MQTT']['mqtt_client_id']
                
                if 'device_name' in config['MQTT']:
                    self.device_name = config['MQTT']['device_name']
            
            logger.debug(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config file {config_path}: {e}")
    
    def save_to_file(self, config_path: str = DEFAULT_CONFIG_PATH) -> bool:
        """Save configuration to a config file."""
        try:
            config = configparser.ConfigParser()
            
            # ANT+ settings
            config['ANT'] = {
                'device_id': str(self.device_id)
            }
            
            # Database settings
            config['Database'] = {
                'db_path': self.db_path
            }
            
            # Display settings
            config['Display'] = {
                'use_terminal_display': str(self.use_terminal_display)
            }
            
            # MQTT settings
            config['MQTT'] = {
                'mqtt_host': self.mqtt_host if self.mqtt_host else '',
                'mqtt_port': str(self.mqtt_port),
                'mqtt_username': self.mqtt_username if self.mqtt_username else '',
                'mqtt_password': self.mqtt_password if self.mqtt_password else '',
                'mqtt_client_id': self.mqtt_client_id,
                'device_name': self.device_name
            }
            
            # Create directory if it doesn't exist
            config_dir = os.path.dirname(config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # Write to file
            with open(config_path, 'w') as f:
                config.write(f)
            
            logger.debug(f"Saved configuration to {config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config file {config_path}: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary."""
        return {
            'device_id': self.device_id,
            'db_path': self.db_path,
            'use_terminal_display': self.use_terminal_display,
            'use_mqtt': self.use_mqtt,
            'mqtt_host': self.mqtt_host,
            'mqtt_port': self.mqtt_port,
            'mqtt_username': self.mqtt_username,
            'mqtt_password': self.mqtt_password,
            'mqtt_client_id': self.mqtt_client_id,
            'device_name': self.device_name,
            'verbose': self.verbose,
            'stats_only': self.stats_only
        }


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Display speed data from ANT+ fitness equipment in large text and/or send to Home Assistant via MQTT.'
    )
    
    # ANT+ settings
    parser.add_argument(
        '-d', '--device-id', 
        type=int, 
        default=DEFAULT_DEVICE_ID,
        help=f'ANT+ device ID to connect to (default: {DEFAULT_DEVICE_ID})'
    )
    
    # Database settings
    parser.add_argument(
        '--db-path',
        type=str,
        default=DEFAULT_DB_PATH,
        help=f'Path to SQLite database file (default: {DEFAULT_DB_PATH})'
    )
    
    # Display settings
    parser.add_argument(
        '--no-terminal',
        action='store_true',
        help='Disable terminal display'
    )
    
    # MQTT settings
    parser.add_argument(
        '--mqtt-host',
        type=str,
        help='MQTT broker hostname or IP address'
    )
    
    parser.add_argument(
        '--mqtt-port',
        type=int,
        default=1883,
        help='MQTT broker port (default: 1883)'
    )
    
    parser.add_argument(
        '--mqtt-username',
        type=str,
        help='MQTT broker username'
    )
    
    parser.add_argument(
        '--mqtt-password',
        type=str,
        help='MQTT broker password'
    )
    
    parser.add_argument(
        '--mqtt-client-id',
        type=str,
        default='ant_speed_display',
        help='MQTT client ID (default: ant_speed_display)'
    )
    
    parser.add_argument(
        '--device-name',
        type=str,
        default='ANT+ Speed Display',
        help='Device name for Home Assistant (default: ANT+ Speed Display)'
    )
    
    # Config file
    parser.add_argument(
        '-c', '--config',
        type=str,
        default=DEFAULT_CONFIG_PATH,
        help=f'Path to config file (default: {DEFAULT_CONFIG_PATH})'
    )
    
    # Other settings
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Display distance statistics and exit'
    )
    
    return parser.parse_args()


def load_config() -> Config:
    """Load configuration from command line arguments and/or config file."""
    args = parse_arguments()
    config = Config()
    
    # Load from config file first
    config.load_from_file(args.config)
    
    # Then override with command line arguments
    config.load_from_args(args)
    
    return config 