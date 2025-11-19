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

        assert printer_config['host'] == '192.168.1.100'
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
            assert printer_config['host'] == '192.168.1.100'
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

        assert config.host == '192.168.1.100'
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


class TestNestingConfig:
    """Tests for NestingConfig and ColumnNestingConfig models."""

    def test_nesting_config_default_creation(self):
        """Test creating NestingConfig with defaults."""
        from taskui.config.nesting_config import NestingConfig

        config = NestingConfig()

        assert config.enabled is True
        assert config.num_columns == 2
        assert config.column1.max_depth == 1
        assert config.column2.max_depth == 1

    def test_nesting_config_with_custom_values(self):
        """Test creating NestingConfig with custom values."""
        from taskui.config.nesting_config import NestingConfig

        config = NestingConfig(
            enabled=False,
            num_columns=3,
            column1={'max_depth': 3, 'display_name': 'Tasks'},
            column2={'max_depth': 5, 'display_name': 'Subtasks'}
        )

        assert config.enabled is False
        assert config.num_columns == 3
        assert config.column1.max_depth == 3
        assert config.column1.display_name == 'Tasks'
        assert config.column2.max_depth == 5
        assert config.column2.display_name == 'Subtasks'

    def test_column_nesting_config_validation(self):
        """Test ColumnNestingConfig field validation."""
        from taskui.config.nesting_config import ColumnNestingConfig
        from pydantic import ValidationError

        # Valid config
        config = ColumnNestingConfig(max_depth=5, display_name="Test")
        assert config.max_depth == 5
        assert config.display_name == "Test"

        # max_depth too high
        with pytest.raises(ValidationError) as exc_info:
            ColumnNestingConfig(max_depth=11)
        assert "less than or equal to 10" in str(exc_info.value)

        # max_depth negative
        with pytest.raises(ValidationError) as exc_info:
            ColumnNestingConfig(max_depth=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

        # display_name too long
        with pytest.raises(ValidationError) as exc_info:
            ColumnNestingConfig(display_name="a" * 51)
        assert "at most 50 characters" in str(exc_info.value)

        # display_name too short
        with pytest.raises(ValidationError) as exc_info:
            ColumnNestingConfig(display_name="")
        assert "at least 1 character" in str(exc_info.value)

    def test_hex_color_validation_valid(self):
        """Test hex color validation with valid colors."""
        from taskui.config.nesting_config import ColumnNestingConfig

        # Valid hex colors
        valid_colors = [
            ["#FF0000", "#00FF00", "#0000FF"],
            ["#ffffff", "#000000"],
            ["#AaBbCc"],
            ["#123456", "#ABCDEF", "#fedcba"],
        ]

        for colors in valid_colors:
            config = ColumnNestingConfig(level_colors=colors)
            assert config.level_colors == colors

    def test_hex_color_validation_invalid(self):
        """Test hex color validation with invalid colors."""
        from taskui.config.nesting_config import ColumnNestingConfig
        from pydantic import ValidationError

        # Invalid hex colors
        invalid_colors = [
            ["#FF00"],           # Too short
            ["#FF00000"],        # Too long
            ["FF0000"],          # Missing #
            ["#GGGGGG"],         # Invalid hex characters
            ["rgb(255,0,0)"],    # Wrong format
            ["#FF 00 00"],       # Spaces
            [""],                # Empty string
        ]

        for colors in invalid_colors:
            with pytest.raises(ValidationError) as exc_info:
                ColumnNestingConfig(level_colors=colors)
            assert "Invalid hex color" in str(exc_info.value)

    def test_nesting_config_num_columns_validation(self):
        """Test num_columns validation."""
        from taskui.config.nesting_config import NestingConfig
        from pydantic import ValidationError

        # Valid
        config = NestingConfig(num_columns=3)
        assert config.num_columns == 3

        # Too low
        with pytest.raises(ValidationError) as exc_info:
            NestingConfig(num_columns=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Too high
        with pytest.raises(ValidationError) as exc_info:
            NestingConfig(num_columns=6)
        assert "less than or equal to 5" in str(exc_info.value)

    def test_nesting_config_from_toml_file_nonexistent(self):
        """Test loading NestingConfig from non-existent file returns defaults."""
        from taskui.config.nesting_config import NestingConfig

        config = NestingConfig.from_toml_file(Path("/tmp/nonexistent_nesting.toml"))

        # Should get defaults
        assert config.enabled is True
        assert config.num_columns == 2
        assert config.column1.max_depth == 1
        assert config.column2.max_depth == 1

    def test_nesting_config_from_toml_file_valid(self):
        """Test loading NestingConfig from valid TOML file."""
        from taskui.config.nesting_config import NestingConfig

        # Create temporary TOML config
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            f.write("""
[nesting]
enabled = true
num_columns = 2

[nesting.column1]
max_depth = 3
display_name = "Tasks"
level_colors = ["#FF0000", "#00FF00"]
context_relative = false

[nesting.column2]
max_depth = 5
display_name = "Subtasks"
level_colors = ["#0000FF", "#FFFF00", "#FF00FF"]
context_relative = true
""")
            config_path = Path(f.name)

        try:
            config = NestingConfig.from_toml_file(config_path)

            assert config.enabled is True
            assert config.num_columns == 2
            assert config.column1.max_depth == 3
            assert config.column1.display_name == "Tasks"
            assert config.column1.level_colors == ["#FF0000", "#00FF00"]
            assert config.column1.context_relative is False
            assert config.column2.max_depth == 5
            assert config.column2.display_name == "Subtasks"
            assert config.column2.level_colors == ["#0000FF", "#FFFF00", "#FF00FF"]
            assert config.column2.context_relative is True
        finally:
            config_path.unlink()

    def test_nesting_config_from_toml_partial(self):
        """Test loading NestingConfig from partial TOML file uses defaults."""
        from taskui.config.nesting_config import NestingConfig

        # Create config with only some values
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            f.write("""
[nesting]
enabled = false

[nesting.column1]
max_depth = 4
""")
            config_path = Path(f.name)

        try:
            config = NestingConfig.from_toml_file(config_path)

            # Specified values
            assert config.enabled is False
            assert config.column1.max_depth == 4

            # Default values
            assert config.num_columns == 2  # Default
            assert config.column2.max_depth == 1  # Default
            assert config.column1.display_name == "Column"  # Default
        finally:
            config_path.unlink()

    def test_nesting_config_from_toml_invalid_colors(self):
        """Test loading NestingConfig with invalid hex colors raises error."""
        from taskui.config.nesting_config import NestingConfig
        from pydantic import ValidationError

        # Create config with invalid hex colors
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            f.write("""
[nesting]
[nesting.column1]
level_colors = ["#GGGGGG", "#HHHHHH"]
""")
            config_path = Path(f.name)

        try:
            with pytest.raises(ValidationError) as exc_info:
                NestingConfig.from_toml_file(config_path)
            assert "Invalid hex color" in str(exc_info.value)
        finally:
            config_path.unlink()

    def test_nesting_config_from_toml_invalid_max_depth(self):
        """Test loading NestingConfig with invalid max_depth raises error."""
        from taskui.config.nesting_config import NestingConfig
        from pydantic import ValidationError

        # Create config with max_depth too high
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            f.write("""
[nesting]
[nesting.column1]
max_depth = 15
""")
            config_path = Path(f.name)

        try:
            with pytest.raises(ValidationError) as exc_info:
                NestingConfig.from_toml_file(config_path)
            assert "less than or equal to 10" in str(exc_info.value)
        finally:
            config_path.unlink()

    def test_nesting_config_from_toml_empty_file(self):
        """Test loading NestingConfig from empty TOML file uses defaults."""
        from taskui.config.nesting_config import NestingConfig

        # Create empty TOML file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            f.write("")
            config_path = Path(f.name)

        try:
            config = NestingConfig.from_toml_file(config_path)

            # Should get all defaults
            assert config.enabled is True
            assert config.num_columns == 2
            assert config.column1.max_depth == 1
            assert config.column2.max_depth == 1
        finally:
            config_path.unlink()

    def test_nesting_config_default_location(self):
        """Test NestingConfig.from_toml_file without path uses default location."""
        from taskui.config.nesting_config import NestingConfig

        # Should not raise even if default location doesn't exist
        config = NestingConfig.from_toml_file()

        # Should get defaults
        assert config.enabled is True
        assert config.num_columns == 2
