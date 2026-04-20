import json
import os
from pathlib import Path


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
    return all(get_env_var(var) for var in required_vars)
