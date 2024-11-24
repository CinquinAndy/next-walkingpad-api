"""
Application configuration
"""
import os
import yaml


class Config:
    """Base configuration"""
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5678

    # WalkingPad settings
    MINIMAL_CMD_SPACE = 0.69

    @classmethod
    def load_yaml_config(cls):
        """Load configuration from yaml file"""
        config_path = os.getenv('CONFIG_PATH', 'config.yaml')
        if os.path.exists(config_path):
            with open(config_path, 'r') as stream:
                try:
                    return yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    print(f"Error loading config: {exc}")
        return {}

    @classmethod
    def get_database_config(cls):
        """Get database configuration"""
        config = cls.load_yaml_config()
        return config.get('database', {})

    @classmethod
    def get_device_address(cls):
        """Get WalkingPad device address"""
        config = cls.load_yaml_config()
        return config.get('address')