"""
Tests for configuration management.

Tests the Config class and configuration loading from files and environment variables.
"""

import os
import tempfile
from pathlib import Path

import pytest

from taskui.config import Config


class TestConfig:
    """Tests for Config class."""

    def test_default_config_path(self):
        """Test default config path is ~/.taskui/config.ini."""
        config = Config()
        expected = Path.home() / ".taskui" / "config.ini"
        assert config.config_path == expected

    def test_custom_config_path(self):
        """Test custom config path is used."""
        custom_path = Path("/tmp/custom_config.ini")
        config = Config(custom_path)
        assert config.config_path == custom_path

    def test_missing_config_file_uses_defaults(self):
        """Test that missing config file falls back to defaults."""
        # Use non-existent path
        config = Config(Path("/tmp/nonexistent_config.ini"))
        printer_config = config.get_printer_config()

        assert printer_config['host'] == '192.168.50.99'
        assert printer_config['port'] == 9100
        assert printer_config['timeout'] == 60
        assert printer_config['detail_level'] == 'minimal'

    def test_config_file_parsing(self):
        """Test parsing valid config file."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            f.write("""
[printer]
host = 192.168.1.100
port = 9200
timeout = 30
detail_level = minimal
""")
            config_path = Path(f.name)

        try:
            config = Config(config_path)
            printer_config = config.get_printer_config()

            assert printer_config['host'] == '192.168.1.100'
            assert printer_config['port'] == 9200
            assert printer_config['timeout'] == 30
            assert printer_config['detail_level'] == 'minimal'
        finally:
            config_path.unlink()

    def test_environment_variable_override(self):
        """Test environment variables override config file."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            f.write("""
[printer]
host = 192.168.1.100
port = 9200
""")
            config_path = Path(f.name)

        try:
            # Set environment variables
            os.environ['TASKUI_PRINTER_HOST'] = '10.0.0.1'
            os.environ['TASKUI_PRINTER_PORT'] = '8888'

            config = Config(config_path)
            printer_config = config.get_printer_config()

            # Environment variables should override file values
            assert printer_config['host'] == '10.0.0.1'
            assert printer_config['port'] == 8888
        finally:
            # Clean up
            config_path.unlink()
            os.environ.pop('TASKUI_PRINTER_HOST', None)
            os.environ.pop('TASKUI_PRINTER_PORT', None)

    def test_partial_config_file(self):
        """Test config file with only some values uses defaults for missing."""
        # Create config with only host
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            f.write("""
[printer]
host = 192.168.1.200
""")
            config_path = Path(f.name)

        try:
            config = Config(config_path)
            printer_config = config.get_printer_config()

            # Specified value
            assert printer_config['host'] == '192.168.1.200'
            # Default values
            assert printer_config['port'] == 9100
            assert printer_config['timeout'] == 60
            assert printer_config['detail_level'] == 'minimal'
        finally:
            config_path.unlink()

    def test_get_methods(self):
        """Test generic get methods."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            f.write("""
[section1]
key1 = value1
int_key = 42
bool_key = true
""")
            config_path = Path(f.name)

        try:
            config = Config(config_path)

            # Test get
            assert config.get('section1', 'key1') == 'value1'
            assert config.get('section1', 'missing', 'default') == 'default'

            # Test get_int
            assert config.get_int('section1', 'int_key') == 42
            assert config.get_int('section1', 'missing', 99) == 99

            # Test get_bool
            assert config.get_bool('section1', 'bool_key') is True
            assert config.get_bool('section1', 'missing', False) is False

            # Test has_section
            assert config.has_section('section1') is True
            assert config.has_section('missing_section') is False

            # Test sections
            assert 'section1' in config.sections()
        finally:
            config_path.unlink()

    def test_invalid_config_file(self):
        """Test handling of invalid config file."""
        # Create invalid config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            f.write("This is not valid INI format @#$%^&*()")
            config_path = Path(f.name)

        try:
            # Should not raise, should fall back to defaults
            config = Config(config_path)
            printer_config = config.get_printer_config()

            # Should get defaults
            assert printer_config['host'] == '192.168.50.99'
            assert printer_config['port'] == 9100
        finally:
            config_path.unlink()


class TestPrinterConfigIntegration:
    """Test PrinterConfig integration with Config module."""

    def test_from_config_file_with_defaults(self):
        """Test loading PrinterConfig from config file with defaults."""
        from taskui.services.printer_service import PrinterConfig, DetailLevel

        # Use non-existent path to trigger defaults
        config = PrinterConfig.from_config_file(Path("/tmp/nonexistent.ini"))

        assert config.host == '192.168.50.99'
        assert config.port == 9100
        assert config.timeout == 60
        assert config.detail_level == DetailLevel.MINIMAL

    def test_from_config_file_with_values(self):
        """Test loading PrinterConfig from actual config file."""
        from taskui.services.printer_service import PrinterConfig, DetailLevel

        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            f.write("""
[printer]
host = 10.0.0.50
port = 8080
timeout = 45
detail_level = minimal
""")
            config_path = Path(f.name)

        try:
            config = PrinterConfig.from_config_file(config_path)

            assert config.host == '10.0.0.50'
            assert config.port == 8080
            assert config.timeout == 45
            assert config.detail_level == DetailLevel.MINIMAL
        finally:
            config_path.unlink()

    def test_from_config_file_invalid_detail_level(self):
        """Test handling of invalid detail_level in config."""
        from taskui.services.printer_service import PrinterConfig, DetailLevel

        # Create config with invalid detail level
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            f.write("""
[printer]
host = 192.168.1.1
detail_level = INVALID_LEVEL
""")
            config_path = Path(f.name)

        try:
            config = PrinterConfig.from_config_file(config_path)

            # Should fall back to MINIMAL
            assert config.detail_level == DetailLevel.MINIMAL
        finally:
            config_path.unlink()
