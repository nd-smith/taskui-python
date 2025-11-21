"""Configuration module for taskui."""

# Import the old Config class from the module-level config.py
# This maintains backward compatibility since config/ package now shadows config.py
import sys
from pathlib import Path

# Temporarily add parent to path to import the old config module
parent_path = str(Path(__file__).parent.parent)
if parent_path not in sys.path:
    sys.path.insert(0, parent_path)

# Try to import Config from the old config module by reading it directly
import importlib.util
config_file = Path(__file__).parent.parent / "config.py"
if config_file.exists():
    spec = importlib.util.spec_from_file_location("_taskui_config_module", config_file)
    if spec and spec.loader:
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        Config = config_module.Config
    else:
        # Fallback if import fails
        Config = None
else:
    Config = None

if Config is not None:
    __all__ = ["Config"]
else:
    __all__ = []
