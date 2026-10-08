import os
from unittest.mock import MagicMock

import discord
import yaml

from utils import config
from utils.checks import is_admin
from utils.formatting import generate_star_rating, review_stars, star_bar


def make_member(user_id=1, administrator=False, role_ids=()):
    member = MagicMock(spec=discord.Member)
    member.id = user_id
    member.guild_permissions.administrator = administrator
    member.roles = [MagicMock(id=r) for r in role_ids]
    return member


def test_star_rendering():
    assert star_bar(10) == "⭐⭐⭐⭐⭐"
    assert star_bar(7) == "⭐⭐⭐✨☆"
    assert review_stars(7) == "⭐⭐⭐✨"
    assert generate_star_rating(0, 0) is None
    assert generate_star_rating(8, 1) == "Rating: ⭐⭐⭐⭐☆ (8.0/10 from 1 review)"


def test_config_save_keeps_order_and_emoji(temp_config):
    data = config.load_config()
    keys = list(data)
    data["tos_decline_response"] = "Nope 🚫"
    config.save_config(data)

    raw = temp_config.read_text(encoding="utf-8")
    assert "Nope 🚫" in raw
    assert list(yaml.safe_load(raw)) == keys


def test_config_reloads_after_external_edit(temp_config):
    assert config.load_config()["auto_close_hours"] == 24
    data = yaml.safe_load(temp_config.read_text(encoding="utf-8"))
    data["auto_close_hours"] = 5
    temp_config.write_text(yaml.safe_dump(data), encoding="utf-8")
    stat = temp_config.stat()
    os.utime(temp_config, (stat.st_atime, stat.st_mtime + 10))
    assert config.load_config()["auto_close_hours"] == 5


def test_load_config_returns_independent_copies(temp_config):
    config.load_config()["forums"].append(1)
    assert 1 not in config.load_config()["forums"]


def test_get_forum_ids_accepts_strings():
    assert config.get_forum_ids({"forums": ["123", 456, "bad"]}) == [123, 456]
    assert config.get_forum_ids({}) == []


def test_is_admin(temp_config):
    data = config.load_config()
    data["admin_ids"] = [42]
    data["admin_role_ids"] = [7]
    config.save_config(data)

    assert is_admin(make_member(42))
    assert is_admin(make_member(1, role_ids=[7]))
    assert is_admin(make_member(1, administrator=True))
    assert not is_admin(make_member(1, role_ids=[8]))
    # Users outside a guild (DMs) are never admins
    assert not is_admin(MagicMock(spec=discord.User, id=42))
