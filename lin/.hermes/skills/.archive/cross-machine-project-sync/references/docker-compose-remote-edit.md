# Docker Compose Python App: Remote Edit Pitfall

When adding new Python files or modifying a Python FastAPI/Flask app running in Docker Compose on a remote machine:

## Check if source is mounted or baked

**Mounted** (`volumes: - .:/app:ro` in docker-compose.yml):
- Edit files on host → changes take effect immediately (uvicorn auto-reloads or just restart container)
- `docker compose restart <service>`

**Baked** (`COPY . .` in Dockerfile, no volume mount for source):
- Edits to host filesystem are invisible to running container
- Must rebuild: `docker compose build <service> && docker compose up -d <service>`
- Rebuild can take 60-120+ seconds for Python images (pip install, etc.)

## How to tell

```bash
# Look at the compose file — is there a volumes entry for the app code?
grep -A3 'volumes:' docker-compose.yml

# Look at the Dockerfile — is there a COPY or ADD?
cat Dockerfile | grep -E '^COPY|^ADD'
```

## The fix if baked

```bash
# Add a volume mount so future edits are live
# In docker-compose.yml, under the service:
volumes:
  - .:/app:ro
```

Then `docker compose up -d` to recreate with the mount. Future edits take effect on restart without rebuild.
