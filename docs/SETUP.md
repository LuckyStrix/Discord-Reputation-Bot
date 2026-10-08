# Setup Guide

This guide takes you from nothing to a running bot. It assumes no prior experience with Discord bots.

## 1. Create the bot application

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
2. Open the **Bot** page:
   - Click **Reset Token** and copy the token. Treat it like a password; anyone with it controls your bot.
   - Under **Privileged Gateway Intents**, turn on **Server Members Intent** and **Message Content Intent**.

## 2. Invite the bot

On the **OAuth2 → URL Generator** page, tick the `bot` and `applications.commands` scopes, then these bot permissions:

| Permission | Why |
|------------|-----|
| View Channels | See the tracked forums and the log channel |
| Send Messages, Send Messages in Threads | Post the TOS prompt, review panel and notices |
| Embed Links | Everything the bot posts is an embed |
| Read Message History | Check whether a reviewer has posted in the thread |
| Manage Messages | Remove messages sent while the TOS prompt is pending |
| Manage Threads | Archive and lock closed posts |

Open the generated URL and add the bot to your server.

## 3. Install

You need **Python 3.11 or newer** ([python.org](https://www.python.org/downloads/)).

```bash
git clone https://github.com/Wk4021/Discord-Reputation-Bot.git
cd Discord-Reputation-Bot
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate      # macOS / Linux
pip install -r requirements.txt
```

On Windows, `RunMe.bat` → **[2] Install/Update requirements** does the install step for you.

## 4. Configure

1. Copy `.env.example` to `.env` and paste your token:
   ```
   DISCORD_TOKEN=your-token-here
   ```
2. Copy `data/config.yaml.example` to `data/config.yaml` and fill in:
   - `forums`: the IDs of the forum channels the bot should manage
   - `log_channel`: a private staff channel for logs
   - `admin_ids` / `admin_role_ids`: optional, since server administrators are always bot admins
   - `tos_message`: point the channel mention at your rules channel

   To copy an ID, enable **Developer Mode** (User Settings → Advanced) and right-click the channel, user or role.

Both files stay on your machine; they are listed in `.gitignore`.

## 5. Run

```bash
python bot.py
```

On Windows you can double-click `RunMe.bat` and choose **[1] Start the bot**.

You should see `✅ Logged in as YourBot#1234`.

## 6. Register the slash commands

Slash commands must be registered with Discord once, and again whenever commands change. In any channel the bot can read, the **bot owner** (the account that owns the application) types:

- `!sync guild`: registers commands in this server only. They appear immediately.
- `!sync`: registers commands globally. They can take up to an hour to appear.

## 7. Try it

1. Create a post in a tracked forum. The bot asks you to accept the TOS.
2. Click **✅ I Agree**. The review panel appears.
3. From another account, post a message in the thread, then click **⭐ Leave a Review**.

Run `/settings` to adjust auto-close, the TOS text and the bot's status.

## Keeping the bot running

`python bot.py` stops when you close the terminal. To keep it running, use a process manager such as `systemd` (Linux), NSSM or Task Scheduler (Windows), or a hosting provider.

## Upgrading

1. Stop the bot.
2. Back up the `data/` folder (it holds `config.yaml` and `rep.db`).
3. Pull the new version and run `pip install -r requirements.txt` again.
4. Start the bot. Database changes are applied automatically on startup.
5. Run `!sync guild` (or `!sync`) if the release notes mention command changes.

### Upgrading from V3.1 or earlier

- The web dashboard has been removed. You can delete `FLASK_SECRET_KEY`, `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI` and `GUILD_ID` from `.env`, and `server_name` / `server_invite` from `config.yaml`.
- Scheduled auto-close times are converted to UTC on first start.
- `/channel_set` and `/log` now require admin rights, and `!sync` only works for the bot owner.
- Optional new setting: `tos_timeout_seconds` (default 30).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `DISCORD_TOKEN is not set` | Create `.env` from `.env.example` and add your token |
| `data/config.yaml not found` | Copy `data/config.yaml.example` to `data/config.yaml` |
| `PrivilegedIntentsRequired` | Enable both intents from step 1 in the Developer Portal |
| Slash commands missing | Run `!sync guild` as the bot owner |
| Bot ignores new posts | Check the forum ID is in `forums` and the bot can see the forum |
| Messages not removed during TOS / posts not locked | Grant **Manage Messages** and **Manage Threads** |
| `ModuleNotFoundError` | Activate the virtual environment and run `pip install -r requirements.txt` |
