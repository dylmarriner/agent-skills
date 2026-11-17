# Telegram Stale Session Lock Recovery — 2026-07-20

## Symptom

`hermes gateway status` showed:

```
⚠ telegram: Telegram polling could not recover after 5 retries (200s total wait).
The previous gateway session is still held open on Telegram's servers, or
another process is using the same bot token. To recover: ensure no other Hermes
or OpenClaw instance is running with this token, then restart the gateway with
'hermes gateway restart'.
```

## What Didn't Work

- `hermes gateway restart` — timed out after 15s (gateway process was stuck in a blocking network call)
- `systemctl --user stop hermes-gateway` — also hung

## What Worked

```bash
# PID was 1795
kill 1795
sleep 2
kill -0 1795 && kill -9 1795   # still alive after SIGTERM, force it
sleep 5                          # critical: let Telegram detect dropped connection
systemctl --user start hermes-gateway
```

## Post-Recovery Verification

After waiting ~15s, the logs showed:

```
[Telegram] set_my_commands OK for scope BotCommandScopeDefault (60 cmds)
[Telegram] set_my_commands OK for scope BotCommandScopeAllPrivateChats (60 cmds)
[Telegram] set_my_commands OK for scope BotCommandScopeAllGroupChats (60 cmds)
[Telegram] Telegram menu: 60 commands registered, 2280 hidden
```

Gateway was then running with 1 platform (Telegram active).

## Environmental Details

- Host: lin (HP Pavilion, Kubuntu)
- Gateway: hermes-gateway.service (systemd --user)
- Bot token env var: `TELEGRAM_BOT_TOKEN`
- Allowed users env var: `TELEGRAM_ALLOWED_USERS`
- Home channel env var: `TELEGRAM_HOME_CHANNEL`
- Gateway config: no explicit `gateway.platforms.telegram` section — uses env vars
- Display config: `display.platforms.telegram.streaming: true`
- Config gateway section (lines 485-489 of config.yaml): `strict: false` only, no platform subsections
- Cron execution DB was also corrupted: `sqlite3.DatabaseError: database disk image is malformed` from `cron/executions.py`
