# Deployment Guide — Cross-Machine Memory Sync

## Machine inventory

| Machine | SSH | Hermes home | Sync script path | Cron status | Gateway |
|---|---|---|---|---|---|
| lin (this) | local | ~/.hermes | ~/.hermes/scripts/sync-memory-to-nexus.py | every 5m | running |
| kubuntux | root@100.93.75.87 | /home/kubuntux/.hermes | /home/kubuntux/.hermes/scripts/sync-memory-to-nexus.py | every 5m | running |
| macuntu | macuntu | /home/macuntu/.hermes | /home/macuntu/.hermes/scripts/sync-memory-to-nexus.py | every 5m | needs start |
| rabuntu | rabuntu | /root/.hermes | /root/.hermes/scripts/sync-memory-to-nexus.py | every 5m | needs start |

## First-time sync commands

```bash
# lin
python3 ~/.hermes/scripts/sync-memory-to-nexus.py

# kubuntux
ssh root@100.93.75.87 'sudo -u kubuntux HOME=/home/kubuntux python3 /home/kubuntux/.hermes/scripts/sync-memory-to-nexus.py'

# macuntu
ssh macuntu 'PATH=$HOME/.local/bin:$PATH python3 $HOME/.hermes/scripts/sync-memory-to-nexus.py'

# rabuntu
ssh rabuntu 'python3 /root/.hermes/scripts/sync-memory-to-nexus.py'
```

## Cron creation

```bash
hermes cron create "every 5m" --name sync-memory-to-nexus --script sync-memory-to-nexus.py --no-agent
```

For non-default user (kubuntux):
```bash
cd /home/kubuntux && sudo -u kubuntux HOME=/home/kubuntux \
  /usr/local/bin/hermes cron create "every 5m" \
  --name sync-memory-to-nexus \
  --script sync-memory-to-nexus.py --no-agent
```

For non-default PATH (macuntu):
```bash
PATH=$HOME/.local/bin:$PATH hermes cron create "every 5m" \
  --name sync-memory-to-nexus \
  --script sync-memory-to-nexus.py --no-agent
```

## Verifying sync

```bash
# Check Nexus admin metrics
curl -s http://100.93.75.87:7777/v1/admin/metrics | python3 -m json.tool

# Check agent profile
curl -s http://100.93.75.87:7777/v1/memory/profile/hermes | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(f'Total: {d[\"total\"]}')
for t,n in d.get('by_type',{}).items():
    print(f'  {t}: {n}')
"
```

## Initial sync results

- lin: 9 entries
- kubuntux: 8 entries
- macuntu: 18 entries
- rabuntu: 0 entries (no local memories yet)

## Swagger UI

FastAPI auto-serves Swagger UI at /docs and ReDoc at /redoc on port 7777. To kill them:
```python
app = FastAPI(..., docs_url=None, redoc_url=None)
```
Then `docker restart nexus-nexus-api-1`. The actual React dashboard is on :7778.

## Docker volume

The real mount is `/home/kubuntux/synapse-memory/` → `/app`. NOT any backup paths like `/media/kubuntux/DEVELOPMENT1/shared-memory/nexus/`. Check with:
```bash
docker inspect nexus-nexus-api-1 --format '{{json .Mounts}}'
```
