# Admin Guide

## Who is an admin?

A member is a bot admin if **any** of these is true:

1. They have the **Administrator** permission in the server (this includes the server owner).
2. Their user ID is in `admin_ids` in `data/config.yaml`.
3. They have a role listed in `admin_role_ids`.

Because server administrators always count, a fresh install can be configured from Discord before anyone is listed in the config.

The bot's **owner** (the account that owns the application in the Developer Portal) is separate: only the owner can run `!sync`.

## Managing admins

| Command | Effect |
|---------|--------|
| `/admin_add @user` | Adds the user to `admin_ids` |
| `/admin_remove @user` | Removes the user from `admin_ids` |
| `/admin_role_add @role` | Adds the role to `admin_role_ids` |
| `/admin_role_remove @role` | Removes the role from `admin_role_ids` |
| `/admin_list` | Lists configured users and roles |

You can also edit `data/config.yaml` directly; the bot notices the change without a restart.

To copy a user or role ID, enable **Developer Mode** (User Settings → Advanced), then right-click the user or role.

## What admins can do

- Run every admin command (see [COMMANDS.md](COMMANDS.md)), including `/settings`
- Close anyone's post with **Close Post**. If `admin_close_confirmation` is on, they confirm by typing "Yes".
- Post a fresh review panel in any thread with `/send_review_ui`

## Safety notes

- Admins can change the log channel, tracked forums and the admin list itself, so choose them carefully.
- Prefer `admin_role_ids` for staff teams: removing someone's role removes their bot access too.
- Every settings change, admin close and auto-close is recorded in the log channel.
- Back up `data/config.yaml` and `data/rep.db` before large changes.
