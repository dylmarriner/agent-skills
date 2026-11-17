# RAGFlow Troubleshooting

## Container Stack (all healthy)

```
NAME                    IMAGE                            PORTS
docker-ragflow-cpu-1   infiniflow/ragflow:v0.26.3        :80, :443, :9380-9384
docker-es01-1          elasticsearch:8.11.3               :9200 (9300 internal)
docker-mysql-1         mysql:8.0.39                       :3306
docker-redis-1         valkey/valkey:8                    :6383
docker-minio-1         pgsty/minio:RELEASE.2026-...       :9000-9001
```

Stack lives at `/mnt/development1/ragflow/docker/`. Bring up with `docker compose up -d`.

## Debug Session (2026-07-07)

### Setup
- All 5 containers Up (healthy): ragflow, mysql, elasticsearch, valkey, minio
- API key and URL set:
  ```bash
  RAGFLOW_API_KEY=ragflow-api-token-hermes
  RAGFLOW_BASE_URL=http://localhost:9380
  ```

### API Works
```bash
curl http://localhost:9380/api/v1/datasets
# → {"code": 0, "data": [{"id": "4ded...", "name": "hermes-knowledge", ...}]}
```

### Issue 1: Health endpoint returns 404
```bash
curl http://localhost:9380/_health
# → 404
curl http://localhost:9380/
# → 404
```
**Normal.** The real API lives under `/api/v1/`. The root and `/` are not
served. Verify with:
```bash
curl -s http://localhost:9380/api/v1/datasets | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"data\"])} datasets')"
```

### Issue 2: Upload fails with "No file part!"
```
POST /api/v1/datasets/{id}/documents → "No file part!"
```
The plugin's `ragflow_upload()` function needs to send multipart/form-data,
not application/json. RAGFlow v0.26.3 expects:
```
POST /api/v1/datasets/{id}/documents
Content-Type: multipart/form-data; boundary=...
--boundary
Content-Disposition: form-data; name="file"; filename="doc.md"
Content-Type: text/markdown

...file content...
--boundary--
```
Check the plugin's HTTP client code at `~/.hermes/plugins/ragflow/__init__.py`
— it may need `multipart/form-data` encoding via `urllib.request` or `requests`.

### Issue 3: Search returns "Provider not found for model ."
```
LookupError: Provider  not found for model .
```
**Root cause:** The dataset has no embedding model assigned. RAGFlow stores
`kb.embd_id = ''` and no provider/instance/model records exist in the new
v0.26.3 tables.

**Embedding model setup for RAGFlow v0.26.3**

RAGFlow v0.26.3 has two separate model systems:
- `tenant_llm` table (legacy, populated by `add_llm` API)
- `tenant_model_provider` + `tenant_model_instance` + `tenant_model` (new,
  populated by `set_api_key` API OR direct DB insert)

The task executor queries the **new** tables via Peewee ORM.
`set_api_key()` both tests the model and creates the new-table records.
It sends a real embedding request — the provider must respond.

**Approach A — Run llama-server on the same Docker network:**

1. Build llama-server from llama.cpp source, or use ollama's nomic-embed-text.
2. Run it as a Docker container on the **same** network as RAGFlow:
   ```bash
   docker run -d --name llama-embed --network docker_ragflow \
     -p 11434:11434 \
     -v /path/to/nomic-embed.gguf:/model.gguf \
     --entrypoint llama-server \
     ubuntu:24.04 \
     -m /model.gguf --host 0.0.0.0 --port 11434 \
     --embeddings --pooling mean --api-key sk-no-key
   ```
   (Or use the prebuilt `llama-embed` Docker image built from the above.)
3. Register the model in the global LLM table:
   ```bash
   docker exec docker-mysql-1 mysql -uroot -pinfini_rag_flow rag_flow \
     -e "INSERT INTO llm (fid, llm_name, model_type, max_tokens, tags, is_tools) \
          VALUES ('OpenAI', 'nomic-embed', 'embedding', 8192, '[]', 0);"
   ```
4. Create provider + instance + model records:
   ```sql
   SET @pid = REPLACE(UUID(), '-', '');
   SET @iid = REPLACE(UUID(), '-', '');
   SET @mid = REPLACE(UUID(), '-', '');
   INSERT INTO tenant_model_provider (id, provider_name, tenant_id)
     VALUES (@pid, 'OpenAI', '<tenant_id>');
   INSERT INTO tenant_model_instance (id, instance_name, provider_id,
     api_key, status, extra)
     VALUES (@iid, 'llama-embed', @pid, 'sk-no-key', 'active',
       '{"api_base":"http://llama-embed:11434/v1"}');
   INSERT INTO tenant_model (id, model_name, provider_id, instance_id,
     model_type, status, extra)
     VALUES (@mid, 'nomic-embed@llama-embed@OpenAI', @pid, @iid,
       'embedding', 'active', '{"max_tokens":8192}');
   ```
5. Update references:
   ```sql
   UPDATE tenant SET embd_id='nomic-embed@llama-embed@OpenAI'
     WHERE id='<tenant_id>';
   UPDATE knowledgebase SET embd_id='nomic-embed@llama-embed@OpenAI'
     WHERE id='<kb_id>';
   ```
6. Disable `--init-model-provider-tables` in docker-compose.yml (it resets
   the new tables on every restart). Comment it out, then restart:
   ```bash
   cd /mnt/development1/ragflow/docker
   docker compose down && docker compose up -d
   ```

**Approach B — Use a cloud embedding API (simpler):**
Set up an OpenAI-compatible API key in the RAGFlow console at
http://localhost:9380. Any provider with an embedding model works (OpenAI,
LiteLLM proxy, etc.). The `set_api_key` flow then succeeds and populates
all three tables automatically.

**Model name format:** RAGFlow's `split_model_name()` parses:
- `model_name` — bare (provider & instance = "")
- `model_name@provider` — 2-part, instance defaults to "default"
- `model_name@instance@provider` — 3-part, fully specified

The 3-part format (`nomic-embed@llama-embed@OpenAI`) is the most explicit.

**Peewee ORM caching:** The new model tables use Peewee with a connection
pool. After inserting records, the task executor may hold a stale connection.
If upload + trigger still fails with "Instance X not found", restart the
RAGFlow container so the task executor reconnects:
```bash
docker restart docker-ragflow-cpu-1
```
Then upload a fresh document + trigger parsing via `/api/v1/datasets/{id}/chunks`.

**Known limitation in v0.26.3:** `set_api_key` with "OpenAI" factory sends the
API key in the Authorization header. llama-server validates it. If the server
rejects the key, `set_api_key` fails and does NOT create the new-table records.
The direct DB insert approach (step 4) bypasses this but requires matching
UUIDs across the three tables.

**Docker network isolation:** RAGFlow containers run on `docker_ragflow`
bridge (172.22.0.x). The host's docker0 bridge is 172.17.0.1. Containers
cannot reach host ports unless the host's UFW has a route allow rule or the
server is containerized on the same network. If running an embedding server
on the host, either:
- Add a UFW rule: `sudo ufw route allow proto tcp from any to any port 11434`
- Or run the embedding server as a container on `docker_ragflow`

### Issue 4: JWT warnings in logs (harmless)
```
WARNING  load_user from jwt got exception No b'.' found in value
```
This fires on every unauthenticated API call. Harmless for local use.

## Quick Health Check Script

```python
import json, os, urllib.request

BASE = os.environ.get("RAGFLOW_BASE_URL", "http://localhost:9380")
KEY = os.environ.get("RAGFLOW_API_KEY", "")

req = urllib.request.Request(f"{BASE}/api/v1/datasets",
    headers={"Authorization": f"Bearer {KEY}"})
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read())
    datasets = data.get("data", [])
    print(f"{len(datasets)} datasets:")
    for ds in datasets:
        print(f"  {ds['name']} ({ds['id']}) — {ds.get('chunk_count', '?')} chunks")
```
