"""Configuration and settings management."""

from typing import Dict, Any
from pathlib import Path


def load_settings() -> Dict[str, Any]:
    """
    Load settings from settings.txt file.

    Returns:
        Dictionary with settings (pixels_per_second, use_bezier)
    """
    # Default settings
    settings = {
        "pixels_per_second": 2000.0,
        "use_bezier": True,
    }

    # Find settings.txt in the project root (parent of src)
    current_dir = Path(__file__).parent
    settings_file = current_dir.parent.parent / "settings.txt"

    if not settings_file.exists():
        return settings

    try:
        with open(settings_file, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse key=value pairs
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    if key == "pixels_per_second":
                        try:
                            settings["pixels_per_second"] = float(value)
                        except ValueError:
                            pass  # Keep default

                    elif key == "use_bezier":
                        settings["use_bezier"] = value.lower() in ("true", "yes", "1", "on")

    except Exception:
        pass  # Keep defaults

    return settings
