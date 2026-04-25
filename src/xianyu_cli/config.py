from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "xianyu-cli"
STATE_FILE_NAME = "storage-state.json"


def get_app_dir() -> Path:
    override = os.environ.get("XIANYU_CLI_HOME")
    if override:
        return Path(override).expanduser()

    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home).expanduser() / APP_DIR_NAME

    return Path.home() / ".config" / APP_DIR_NAME


def get_default_storage_state_path() -> Path:
    return get_app_dir() / STATE_FILE_NAME


def resolve_storage_state_path(path: str | None) -> Path:
    if path:
        return Path(path).expanduser()
    return get_default_storage_state_path()
