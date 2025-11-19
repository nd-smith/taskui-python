"""Nesting configuration models for taskui.

This module provides Pydantic models for configuring the column nesting feature,
including per-column settings and TOML file loading support.
"""

from pathlib import Path
from typing import List
import sys
import logging
import re

# Use tomllib from stdlib in Python 3.11+, fallback to tomli for earlier versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ColumnNestingConfig(BaseModel):
    """Configuration for a single column's nesting behavior.

    Attributes:
        max_depth: Maximum nesting depth allowed (0-10).
        display_name: Human-readable name for the column (1-50 characters).
        level_colors: List of hex color codes for indentation levels.
        context_relative: Whether to use context-relative positioning.
    """

    max_depth: int = Field(default=1, ge=0, le=10)
    display_name: str = Field(default="Column", min_length=1, max_length=50)
    level_colors: List[str] = Field(default=["#66D9EF", "#A6E22E"])
    context_relative: bool = Field(default=False)

    @field_validator('level_colors')
    @classmethod
    def validate_hex_colors(cls, v: List[str]) -> List[str]:
        """Validate that all colors are valid hex codes.

        Args:
            v: List of color strings to validate.

        Returns:
            The validated list of hex colors.

        Raises:
            ValueError: If any color is not a valid hex code.
        """
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        for i, color in enumerate(v):
            if not hex_pattern.match(color):
                raise ValueError(f"Invalid hex color at index {i}: '{color}'")
        return v


class NestingConfig(BaseModel):
    """Root nesting configuration.

    Attributes:
        enabled: Whether nesting functionality is enabled.
        num_columns: Number of columns to display (1-5).
        column1: Configuration for the first column.
        column2: Configuration for the second column.
    """

    enabled: bool = True
    num_columns: int = Field(default=2, ge=1, le=5)

    column1: ColumnNestingConfig = Field(default_factory=ColumnNestingConfig)
    column2: ColumnNestingConfig = Field(default_factory=ColumnNestingConfig)

    @classmethod
    def from_toml_file(cls, path: Path = None) -> 'NestingConfig':
        """Load configuration from TOML file with fallback to defaults.

        Args:
            path: Path to the TOML configuration file. If None, defaults to
                  ~/.taskui/nesting.toml.

        Returns:
            NestingConfig instance loaded from file or with default values.

        Note:
            If the file doesn't exist, returns a default configuration and
            logs an informational message.
        """
        if path is None:
            path = Path.home() / ".taskui" / "nesting.toml"

        if not path.exists():
            logger.info(f"Config not found at {path}. Using defaults.")
            return cls()

        with open(path, 'rb') as f:
            data = tomllib.load(f)

        return cls(**data.get('nesting', {}))
