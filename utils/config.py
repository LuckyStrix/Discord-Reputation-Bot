"""Reads and writes the bot's YAML configuration (data/config.yaml)."""
import copy
import os
import tempfile
from pathlib import Path

import yaml

# Resolve paths from the project root so the bot works no matter which
# directory it is started from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / 'data' / 'config.yaml'

_cache: dict | None = None
_cache_mtime: float | None = None


def load_config() -> dict:
    """
    Return the current configuration.

    The file is re-read only when it changes on disk, so manual edits still
    take effect without a restart. Callers get their own copy and may modify
    it freely before passing it to save_config().
    """
    global _cache, _cache_mtime
    mtime = os.path.getmtime(CONFIG_PATH)
    if _cache is None or mtime != _cache_mtime:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            _cache = yaml.safe_load(f) or {}
        _cache_mtime = mtime
    return copy.deepcopy(_cache)


def save_config(config: dict) -> None:
    """Write the configuration atomically, keeping key order and emoji readable."""
    global _cache, _cache_mtime
    fd, tmp_path = tempfile.mkstemp(dir=CONFIG_PATH.parent, prefix='.config-', suffix='.yaml')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)
        os.replace(tmp_path, CONFIG_PATH)
    except BaseException:
        os.unlink(tmp_path)
        raise
    _cache = copy.deepcopy(config)
    _cache_mtime = os.path.getmtime(CONFIG_PATH)


def get_forum_ids(config: dict) -> list[int]:
    """Tracked forum channel IDs as ints (YAML may hold them as strings)."""
    return [int(f) for f in config.get("forums") or [] if str(f).isdigit()]
