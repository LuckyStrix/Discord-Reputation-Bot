"""Shared actions on marketplace threads and the log channel."""
import time

import discord

from utils import db
from utils.config import load_config


async def send_log(client: discord.Client, embed: discord.Embed) -> None:
    """Send an embed to the configured log channel, if there is one."""
    log_ch_id = load_config().get("log_channel")
    if not log_ch_id:
        return
    log_ch = client.get_channel(log_ch_id)
    if not log_ch:
        return
    if embed.timestamp is None:
        embed.timestamp = discord.utils.utcnow()
    try:
        await log_ch.send(embed=embed)
    except discord.HTTPException as e:
        print(f"[WARN] Could not send to log channel {log_ch_id}: {e}")


async def update_thread_log(client: discord.Client, thread: discord.Thread, **kwargs) -> None:
    """Update the per-thread log embed via the LoggingSystem cog, if loaded."""
    logging_cog = client.get_cog("LoggingSystem")
    if logging_cog:
        await logging_cog.update_thread_log(thread, **kwargs)


async def close_thread(client: discord.Client, thread: discord.Thread, status: str) -> None:
    """
    Archive and lock a thread, record it in the database and set its
    "Thread Status" in the thread log.

    `status` is the log text, e.g. "❌ Closed"; the time is appended.
    """
    await update_thread_log(
        client, thread,
        field_updates={"Thread Status": f"{status} at <t:{int(time.time())}:T>"}
    )
    await thread.edit(archived=True, locked=True)
    db.mark_thread_closed(thread.id)
