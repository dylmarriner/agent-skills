# RAGFlow Setup & Integration

## Deployment

RAGFlow runs via Docker compose at `/mnt/development1/ragflow/docker/`:

```bash
cd /mnt/development1/ragflow/docker
docker compose up -d
```

This starts: Elasticsearch (search), MySQL (metadata), Redis (cache), MinIO (object storage), and the RAGFlow API server.

## First-Time Setup

1. After containers start, open http://localhost:9380 in browser
2. Register an admin account (first user becomes admin)
3. Go to Console → API Keys — generate an API key
4. Set env vars:

```bash
export RAGFLOW_API_KEY="ragflow-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export RAGFLOW_BASE_URL="http://localhost:9380"
```

## Hermes Integration

The ragflow Hermes plugin registers 5 tools:

| Tool | Endpoint | Purpose |
|------|----------|---------|
| `ragflow_health` | `/_health` | Server health check |
| `ragflow_datasets` | `GET/POST /api/v1/datasets` | List or create knowledge bases |
| `ragflow_upload` | `POST /api/v1/datasets/{id}/documents` | Upload files for indexing |
| `ragflow_search` | `POST /api/v1/retrieval` | Hybrid search (BM25 + vector) |
| `ragflow_chat` | Retrieval + context | RAG query with retrieved chunks |

## Workflow

1. Create a dataset: `ragflow_datasets({"action": "create", "name": "docs"})`
2. Upload documents: `ragflow_upload({"dataset_id": "id", "file_path": "/path/to/doc.pdf"})`
3. Wait for indexing (async — check via dataset list)
4. Search: `ragflow_search({"dataset_id": "id", "query": "your question"})`
5. Chat with context: `ragflow_chat({"dataset_id": "id", "question": "your question"})`

## SDK

```bash
pip install ragflow-sdk
```

```python
import ragflow_sdk
rag = ragflow_sdk.RAGFlow(api_key="...", base_url="http://localhost:9380")
ds = rag.create_dataset("my-docs")
ds.upload_documents(["file1.pdf"])
chunks = ds.search("query text")
```
