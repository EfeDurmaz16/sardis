"""Configuration management for Sardis CLI."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

# Default configuration directory
CONFIG_DIR = Path.home() / ".sardis"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "api_base_url": "https://api.sardis.network",
    "default_chain": "base_sepolia",
}


def ensure_config_dir() -> Path:
    """Ensure configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> Dict[str, Any]:
    """Load configuration from file and environment."""
    config = DEFAULT_CONFIG.copy()
    
    # Load from file if exists
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                file_config = json.load(f)
                config.update(file_config)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Override with environment variables
    if os.environ.get("SARDIS_API_KEY"):
        config["api_key"] = os.environ["SARDIS_API_KEY"]
    if os.environ.get("SARDIS_API_BASE_URL"):
        config["api_base_url"] = os.environ["SARDIS_API_BASE_URL"]
    if os.environ.get("SARDIS_DEFAULT_CHAIN"):
        config["default_chain"] = os.environ["SARDIS_DEFAULT_CHAIN"]
    
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    ensure_config_dir()
    
    # Don't save sensitive data from environment
    save_data = {k: v for k, v in config.items() if k != "verbose"}
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(save_data, f, indent=2)
    
    # Set restrictive permissions
    CONFIG_FILE.chmod(0o600)


def get_api_key() -> str | None:
    """Get API key from config or environment."""
    config = load_config()
    return config.get("api_key")


def get_api_base_url() -> str:
    """Get API base URL."""
    config = load_config()
    return config.get("api_base_url", DEFAULT_CONFIG["api_base_url"])

