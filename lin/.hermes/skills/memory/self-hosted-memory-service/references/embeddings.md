# Embeddings: enabling and verifying vector recall

Lexical (BM25) search is on by default, vectors are opt-in. Turn them on when recall
has to survive paraphrase — a query like "which computer does he rely on" must find a
note that says "HP Pavilion 15 running Kubuntu", which shares no keywords with it.

## Three config touchpoints (packaged config.yaml)

```yaml
components:
  as_embedding:
    default:
      backend: ${EMBEDDING_BACKEND:-openai}      # any OpenAI-compatible /embeddings
      model: ${EMBEDDING_MODEL_NAME:-<model>}
      dimensions: ${EMBEDDING_DIMENSIONS:-<model's real output dim>}
      credential:
        api_key: ${EMBEDDING_API_KEY:-}
        base_url: ${EMBEDDING_BASE_URL:-<base>}
  embedding_store:
    default:
      backend: local
      as_embedding: default
  file_store:
    default:
      embedding_store: default                   # ships as "" — this is the switch
```

These blocks ship commented out, and positional `a.b.c=value` start-line overrides
cannot add what is not in the tree — so this is one of the cases where editing the
packaged yaml is correct. It is a tracked file: the checkout goes dirty, and
`git checkout <path>` reverts it (the same values can be re-applied as overrides
later if the user prefers a clean tree).

```ini
EMBEDDING_BACKEND=openai
EMBEDDING_MODEL_NAME=<model id>
EMBEDDING_DIMENSIONS=<width the API actually returns>
EMBEDDING_API_KEY=<key>
EMBEDDING_BASE_URL=<base url>
```

Env goes in the unit's `EnvironmentFile` like the LLM vars — see `references/reme.md`.
A mismatch between `dimensions` and the model's real width is the classic silent
breakage, so take the width from a live response, not from documentation.

## Probe the provider before wiring it

```bash
curl -s <base>/embeddings -H "Authorization: Bearer $KEY" \
  -H 'Content-Type: application/json' -d '{"model":"<id>","input":"hello"}' \
| python3 -c 'import json,sys; print(len(json.load(sys.stdin)["data"][0]["embedding"]))'
```

Read the status literally: `200` works; `402` the account has no balance; `404`
"not found for account" means the id is listed but not entitled; `410` the model has
reached end of life. Catalog lists are not entitlements and models do expire, so probe
the exact id you intend to use rather than picking one off `/v1/models`.

Choices in practice: a free NIM account can serve an embed model (e.g.
`nvidia/nemotron-3-embed-1b`, 2048d); OpenAI `text-embedding-3-small` (1536d) costs so
little that a personal knowledge base is effectively free; a local llama-server or
ollama exposing `/embeddings` needs no key and keeps everything on the box.

## Switching model or dimension: wipe, then reindex

Vectors are cached under `<workspace>/metadata/embedding_store/default_v1_<hash>.npz`,
keyed to the old width.

```bash
systemctl --user stop <tool>
rm -rf <workspace>/metadata/embedding_store     # rebuildable by design
systemctl --user start <tool>
<tool> reindex scope=all
```

Confirm from the service log: `[EMBEDDING HEALTH CHECK] ... -> OK` (proves the
endpoint answers), `embedding backfill complete: filled=N/N`, and a fresh `.npz`
written under `metadata/embedding_store/`.

## Verify semantic recall — the only real proof

```bash
<tool> write path=digest/wiki/embed-probe name=Probe description=probe \
  content="# Probe

<fact phrased nothing like the query>"
sleep 8                                          # watcher + backfill
<tool> search query="<paraphrase with zero keyword overlap>" limit=3
```

What the score line means: `[score=...]` alone is a vector-only hit (the goal);
`vector=... keyword=...` shows the components when both matched; a lexical-only hit
carries a `keyword=` component without `vector=`. Zero hits means embeddings are not
in play — unwired, or the store never reindexed after the switch.

Finish by deleting the probe and reindexing, then re-run the query to confirm the
store is back to the user's own data.
