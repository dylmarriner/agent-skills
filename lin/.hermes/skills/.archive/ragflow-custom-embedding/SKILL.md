---
name: ragflow-custom-embedding
description: Set up a custom embedding model for RAGFlow v0.26.x — from building llama-server to registering the model provider in RAGFlow's multi-table provider system.
---

# RAGFlow Custom Embedding Model Setup

Build and deploy a custom embedding model (e.g. `nomic-embed-text` via llama.cpp's `llama-server`) and wire it into RAGFlow's model provider system.

## Prerequisites

- RAGFlow Docker stack running (Docker Compose at `/path/to/ragflow/docker/`)
- Access to a GGUF embedding model (from HuggingFace or Ollama cache)
- llama.cpp source code for building `llama-server`

## Overview

```
GGUF model → llama-server (Docker container on ragflow network)
  → RAGFlow global llm table + llm_factories.json
  → tenant_model_provider + tenant_model_instance + tenant_model
  → Knowledgebase embd_id → document parsing + embedding
```

## Step 1: Build llama-server

llama.cpp `llama-server` binary serves the OpenAI-compatible `/v1/embeddings` endpoint.

**Build locally, NOT on an SMB/CIFS mount** — symlinks fail on CIFS:

```bash
# Copy source locally
cp -r /path/to/llama.cpp /tmp/llama.cpp && rm -rf /tmp/llama.cpp/build

# Configure with server target
mkdir -p /tmp/llama.cpp/build && cd /tmp/llama.cpp/build
cmake .. -DLLAMA_BUILD_SERVER=ON -DCMAKE_BUILD_TYPE=Release
cmake --build . --target llama-server -j$(nproc)
```

The binary is at `build/bin/llama-server`.

## Step 2: Get an embedding GGUF model

**From HuggingFace (recommended):**

```python
from huggingface_hub import hf_hub_download
path = hf_hub_download(
    repo_id='nomic-ai/nomic-embed-text-v1.5-GGUF',
    filename='nomic-embed-text-v1.5.Q4_K_M.gguf'
)
```

**From Ollama cache** (already downloaded by `ollama pull`):

```bash
ls ~/.ollama/models/blobs/sha256-*
# The blobs are SHA256 hashes — identify the right one by checking which model
```

## Step 3: Package llama-server in a Docker container

**Create Dockerfile:**

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY *.so* /usr/local/lib/
RUN ldconfig /usr/local/lib/
COPY llama-server /usr/local/bin/
COPY model.gguf /model.gguf
EXPOSE 11434
ENTRYPOINT ["llama-server", "-m", "/model.gguf", "--host", "0.0.0.0", "--port", "11434", "--embeddings", "--pooling", "mean"]
```

**Critical: copy ALL shared libraries + symlinks** from the build output:

```bash
cp build/bin/llama-server /tmp/docker-build/
for lib in build/bin/*.so*; do cp "$lib" /tmp/docker-build/; done
```

**Why ubuntu:24.04, not 22.04:** The llama.cpp shared libs are compiled against GLIBC 2.38+, which is only in Ubuntu 24.04+. Ubuntu 22.04 has GLIBC 2.35 and will fail at runtime.

**Build and run on the RAGFlow Docker network:**

```bash
docker build -t llama-embed:latest /tmp/docker-build/
docker run -d --name llama-embed --network docker_ragflow \
  -p 11434:11434 \
  llama-embed:latest
```

If the API key is validated by the server, restart with `--api-key sk-no-key`.

## Step 4: Verify embedding endpoint from RAGFlow container

```bash
docker exec docker-ragflow-cpu-1 curl -s --max-time 10 \
  http://llama-embed:11434/v1/embeddings \
  -H "Authorization: Bearer sk-no-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"nomic-embed","input":"hello"}' | head -c 80
```

## Step 5: Register model in RAGFlow (v0.26.x)

RAGFlow has a multi-table model provider system:

### 5a. Seed global `llm_factories` table (if empty)

The `--init-model-provider-tables` compose flag seeds these on restart — but it may wipe custom inserts. Better to **disable the flag** in docker-compose.yml first, then manually seed:

```sql
INSERT INTO llm_factories (name, tags, status, `rank`) VALUES 
('OpenAI', 'cloud', '1', 0),
('Ollama', 'self_deployed', '1', 10),
('LocalAI', 'self_deployed', '1', 5),
('FastEmbed', 'self_deployed', '1', 1);
```

### 5b. Register model in global `llm` table

```sql
INSERT INTO llm (fid, llm_name, model_type, max_tokens, tags, is_tools) VALUES 
('OpenAI', 'nomic-embed', 'embedding', 8192, '[]', 0);
```

### 5c. Add model to `llm_factories.json`

This file (`/ragflow/conf/llm_factories.json` inside the container) defines the **hardcoded model list per factory**. `nomic-embed` isn't in OpenAI's default list, so the task executor's `get_model_config_from_provider_instance` will fail at line 299 unless you add it:

```python
import json
with open('/ragflow/conf/llm_factories.json') as f:
    d = json.load(f)
for fi in d['factory_llm_infos']:
    if fi['name'] == 'OpenAI':
        fi['llm'].append({
            'llm_name': 'nomic-embed',
            'tags': 'embedding',
            'max_tokens': 8192,
            'model_type': ['embedding', 'text2text']
        })
with open('/ragflow/conf/llm_factories.json', 'w') as f:
    json.dump(d, f, indent=2)
```

### 5d. Create tenant-level provider/instance/model records

```sql
SET @pid = REPLACE(UUID(), '-', '');
SET @iid = REPLACE(UUID(), '-', '');
SET @mid = REPLACE(UUID(), '-', '');
INSERT INTO tenant_model_provider (id, provider_name, tenant_id) 
  VALUES (@pid, 'OpenAI', '<tenant_id>');
INSERT INTO tenant_model_instance (id, instance_name, provider_id, api_key, status, extra) 
  VALUES (@iid, 'llama-embed', @pid, 'sk-no-key', 'active', 
    '{"base_url":"http://llama-embed:11434/v1"}');
INSERT INTO tenant_model (id, model_name, provider_id, instance_id, model_type, status, extra) 
  VALUES (@mid, 'nomic-embed@llama-embed@OpenAI', @pid, @iid, 'embedding', 'active', 
    '{"max_tokens":8192}');
```

**⚠ Critical:** The `extra` field on `tenant_model_instance` uses `base_url`, NOT `api_base`. Using the wrong key name silently results in an empty base URL and authentication errors.

### 5e. Set default embedding model

```sql
UPDATE tenant SET embd_id='nomic-embed@llama-embed@OpenAI' WHERE id='<tenant_id>';
UPDATE knowledgebase SET embd_id='nomic-embed@llama-embed@OpenAI' WHERE id='<kb_id>';
```

The model name format is: `{model_name}@{instance_name}@{provider_name}`

### 5f. Restart after any JSON changes

```bash
docker restart docker-ragflow-cpu-1
```

## Step 6: Upload and parse a document

```bash
# Upload
curl -s -X POST "http://localhost:9380/api/v1/datasets/<kb_id>/documents" \
  -H "Authorization: Bearer <token>" \
  -F "file=@doc.md"

# Trigger chunking
curl -s -X POST "http://localhost:9380/api/v1/datasets/<kb_id>/chunks" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"document_ids":["<doc_id>"]}'
```

## Step 7: Search

```bash
curl -s -X POST "http://localhost:9380/api/v1/datasets/<kb_id>/search" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question":"your query"}'
```

## Verification

- **ES index**: check `curl -u elastic:password "http://localhost:1200/_cat/indices?v"`
- **Chunk data**: check `q_768_vec` field in ES doc (must have 768 floats)
- **Run status**: `SELECT name, run, chunk_num FROM document` — run=3 is SUCCESS, run=4 is ERROR

## Reference Files

- `references/llama-server-build.md` — Build llama-server from source, GLIBC compat, Docker packaging
- `references/ragflow-model-system.md` — RAGFlow model schema, code flow, Peewee ORM issues
- `references/docker-networking-ragflow.md` — Cross-container networking with UFW on Docker

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| llama-server on SMB mount | cmake fails "Operation not supported" on symlink | Build locally (`/tmp/`) |
| Wrong Ubuntu base image | `GLIBC_2.38 not found` | Use `ubuntu:24.04` |
| UFW blocking Docker | Container can't reach host port | Run on same Docker network |
| `extra` key wrong | OpenAI 401 auth error | Use `base_url` not `api_base` |
| Model not in `llm_factories.json` | "Instance not found" at line 299 | Add to JSON file |
| Stale Peewee connections | ORM returns None despite DB data | Kill task executor or restart container |
| Init flag wiping inserts | Data disappears after restart | Comment out `--init-model-provider-tables` in compose |
