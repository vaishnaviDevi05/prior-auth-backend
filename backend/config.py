import json
import os
from pathlib import Path


PLACEHOLDER_MARKERS = (
    "YOUR-RESOURCE",
    "YOUR-KEY",
    "your-resource",
    "your-key",
    "example",
    "changeme",
)


def _is_real_config_value(value: str) -> bool:
    if not value:
        return False

    normalized = value.strip()
    if not normalized:
        return False

    upper_value = normalized.upper()
    return not any(marker.upper() in upper_value for marker in PLACEHOLDER_MARKERS)


def load_config():
    """Load configuration from backend/config.json and set environment variables."""
    try:
        config_path = Path(__file__).with_name("config.json")
        with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)

        for key, value in config.items():
            if value and not os.getenv(key):
                os.environ[key] = value

        return True
    except Exception:
        return False


def get_env_var(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def is_configured() -> bool:
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_API_VERSION",
    ]
    return all(_is_real_config_value(get_env_var(var)) for var in required_vars)
