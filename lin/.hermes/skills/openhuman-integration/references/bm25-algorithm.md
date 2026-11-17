# BM25-Okapi Ranking Algorithm

Used by the codegraph plugin for ranked code search.

## Formula

```
score(D, Q) = Σ_{term in Q} IDF(term) × (tf(term, D) × (k₁ + 1)) / (tf(term, D) + k₁ × (1 - b + b × |D| / avgdl))
```

Where:
- `tf(term, D)` — term frequency in document D
- `|D|` — length of document D (in tokens)
- `avgdl` — average document length across the corpus
- `k₁ = 1.5` — term frequency saturation parameter
- `b = 0.75` — length normalization parameter
- `IDF(term) = log((N - df + 0.5) / (df + 0.5) + 1)` — inverse document frequency

## Tokenization

Code tokens are extracted by:
1. Finding identifiers via `[a-zA-Z_][a-zA-Z0-9_]{0,50}`
2. Splitting camelCase → sub-words (`createDatabase` → `create`, `database`)
3. Splitting snake_case → sub-words (`create_database` → `create`, `database`)
4. Lowercasing all tokens
5. Filtering stop words (common English + programming keywords: `the`, `get`, `set`, `new`, etc.)
6. Filtering single-character tokens

## Implementation

The BM25Index class builds from a list of documents, each with an identifier (file path) and token list. `search()` scores all documents against the query and returns top-K by score.

```python
idx = BM25Index()
idx.add_document("src/api/auth.py", ["create", "token", "user", "authenticate"])
idx.add_document("src/api/db.py", ["connect", "pool", "database", "query"])
idx.build()
results = idx.search("database authentication")
# Returns: [("src/api/db.py", 0.83), ("src/api/auth.py", 0.45)]
```

## Per-document score components

- **Term frequency (tf):** How often the query term appears in the document. Capped by k₁ saturation.
- **Inverse document frequency (idf):** How rare the term is across all documents. Rare terms get higher weight.
- **Length normalization (b):** Longer documents get a slight penalty since they have more terms by volume.
