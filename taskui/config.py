"""
Configuration management for TaskUI.

Loads settings from config.ini with environment variable overrides.
Provides centralized configuration for all TaskUI components.
"""

import configparser
import os
from pathlib import Path
from typing import Optional, Dict, Any

from taskui.logging_config import get_logger

logger = get_logger(__name__)


class Config:
    """Application configuration manager."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to config file, defaults to config/settings.ini
        """
        self.config_path = config_path or self._default_config_path()
        self._config = configparser.ConfigParser()
        self._load()

    def _default_config_path(self) -> Path:
        """Get default config path."""
        project_root = Path(__file__).parent.parent
        return project_root / "config" / "settings.ini"

    def _load(self):
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                self._config.read(self.config_path)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to read config file: {e}. Using defaults.")
        else:
            logger.debug(f"Config file not found at {self.config_path}. Using defaults.")

    def get_printer_config(self) -> Dict[str, Any]:
        """
        Get printer configuration with environment overrides.

        Environment variables take precedence over config file:
        - TASKUI_PRINTER_HOST
        - TASKUI_PRINTER_PORT
        - TASKUI_PRINTER_TIMEOUT
        - TASKUI_PRINTER_DETAIL_LEVEL
        - TASKUI_PRINTER_INCLUDE_DIARY_ENTRIES

        Returns:
            Dictionary with printer configuration
        """
        config = {
            'host': os.getenv('TASKUI_PRINTER_HOST') or
                   self._config.get('printer', 'host', fallback='192.168.1.100'),
            'port': int(os.getenv('TASKUI_PRINTER_PORT') or
                       self._config.get('printer', 'port', fallback='9100')),
            'timeout': int(os.getenv('TASKUI_PRINTER_TIMEOUT') or
                          self._config.get('printer', 'timeout', fallback='60')),
            'detail_level': os.getenv('TASKUI_PRINTER_DETAIL_LEVEL') or
                           self._config.get('printer', 'detail_level', fallback='minimal'),
            'include_diary_entries': (
                os.getenv('TASKUI_PRINTER_INCLUDE_DIARY_ENTRIES', '').lower() == 'true'
                if os.getenv('TASKUI_PRINTER_INCLUDE_DIARY_ENTRIES')
                else self._config.getboolean('printer', 'include_diary_entries', fallback=True)
            ),
        }

        logger.debug(f"Printer config: host={config['host']}, port={config['port']}, "
                    f"detail_level={config['detail_level']}, "
                    f"include_diary_entries={config['include_diary_entries']}")

        return config

    def get_cloud_print_config(self) -> Dict[str, Any]:
        """
        Get cloud print queue configuration with environment overrides.

        Environment variables take precedence over config file:
        - TASKUI_CLOUD_QUEUE_URL
        - TASKUI_CLOUD_REGION
        - TASKUI_CLOUD_MODE (direct/cloud/auto)
        - TASKUI_ENCRYPTION_KEY (base64-encoded encryption key)
        - AWS_ACCESS_KEY_ID (standard AWS env var)
        - AWS_SECRET_ACCESS_KEY (standard AWS env var)

        Returns:
            Dictionary with cloud print configuration
        """
        config = {
            'queue_url': os.getenv('TASKUI_CLOUD_QUEUE_URL') or
                        self._config.get('cloud_print', 'queue_url', fallback=''),
            'region': os.getenv('TASKUI_CLOUD_REGION') or
                     self._config.get('cloud_print', 'region', fallback='us-east-1'),
            'mode': os.getenv('TASKUI_CLOUD_MODE') or
                   self._config.get('cloud_print', 'mode', fallback='auto'),
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID') or
                                self._config.get('cloud_print', 'aws_access_key_id', fallback=None),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY') or
                                    self._config.get('cloud_print', 'aws_secret_access_key', fallback=None),
            'encryption_key': os.getenv('TASKUI_ENCRYPTION_KEY') or
                            self._config.get('cloud_print', 'encryption_key', fallback=None),
        }

        encryption_status = "enabled" if config.get('encryption_key') else "disabled"
        logger.debug(f"Cloud print config: region={config['region']}, mode={config['mode']}, encryption={encryption_status}")

        return config

    def get_display_config(self) -> Dict[str, Any]:
        """
        Get display configuration with environment overrides.

        Environment variables take precedence over config file:
        - TASKUI_DISPLAY_TIMEZONE

        Returns:
            Dictionary with display configuration
        """
        config = {
            'timezone': os.getenv('TASKUI_DISPLAY_TIMEZONE') or
                       self._config.get('display', 'timezone', fallback='America/Denver'),
        }

        logger.debug(f"Display config: timezone={config['timezone']}")

        return config

    def get_sync_config(self) -> Dict[str, Any]:
        """
        Get sync configuration with environment overrides.

        Environment variables take precedence over config file:
        - TASKUI_SYNC_ENABLED
        - TASKUI_SYNC_QUEUE_URL
        - TASKUI_SYNC_REGION
        - TASKUI_SYNC_ON_OPEN

        Returns:
            Dictionary with sync configuration
        """
        enabled_env = os.getenv('TASKUI_SYNC_ENABLED', '').lower()
        enabled = (
            enabled_env == 'true'
            if enabled_env
            else self._config.getboolean('sync', 'enabled', fallback=False)
        )

        sync_on_open_env = os.getenv('TASKUI_SYNC_ON_OPEN', '').lower()
        sync_on_open = (
            sync_on_open_env == 'true'
            if sync_on_open_env
            else self._config.getboolean('sync', 'sync_on_open', fallback=True)
        )

        config = {
            'enabled': enabled,
            'queue_url': os.getenv('TASKUI_SYNC_QUEUE_URL') or
                        self._config.get('sync', 'queue_url', fallback=''),
            'region': os.getenv('TASKUI_SYNC_REGION') or
                     self._config.get('sync', 'region', fallback='us-east-1'),
            'sync_on_open': sync_on_open,
        }

        logger.debug(f"Sync config: enabled={config['enabled']}, "
                    f"region={config['region']}, sync_on_open={config['sync_on_open']}")

        return config

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """
        Get configuration value with fallback.

        Args:
            section: Config section name
            key: Config key name
            fallback: Default value if not found

        Returns:
            Configuration value or fallback
        """
        return self._config.get(section, key, fallback=fallback)

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """
        Get boolean configuration value.

        Args:
            section: Config section name
            key: Config key name
            fallback: Default value if not found

        Returns:
            Boolean configuration value or fallback
        """
        return self._config.getboolean(section, key, fallback=fallback)

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """
        Get integer configuration value.

        Args:
            section: Config section name
            key: Config key name
            fallback: Default value if not found

        Returns:
            Integer configuration value or fallback
        """
        return self._config.getint(section, key, fallback=fallback)

    def has_section(self, section: str) -> bool:
        """
        Check if config section exists.

        Args:
            section: Section name to check

        Returns:
            True if section exists
        """
        return self._config.has_section(section)

    def sections(self) -> list:
        """
        Get list of all configuration sections.

        Returns:
            List of section names
        """
        return self._config.sections()


# Example usage and testing
if __name__ == "__main__":
    from taskui.logging_config import setup_logging

    setup_logging()

    # Test configuration loading
    config = Config()

    print("Configuration sections:", config.sections())
    print("\nPrinter configuration:")
    printer_config = config.get_printer_config()
    for key, value in printer_config.items():
        print(f"  {key}: {value}")

    # Test environment variable override
    os.environ['TASKUI_PRINTER_HOST'] = '192.168.1.100'
    config2 = Config()
    print("\nPrinter config with env override:")
    print(f"  host: {config2.get_printer_config()['host']}")
