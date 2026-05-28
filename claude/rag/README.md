# Local RAG Knowledge Base

Lightweight local vector search replacing grep for knowledge base queries.

## Quick Start

```bash
# Step 1: Install dependencies
cd ~/.config/opencode/rag
pip install -r requirements.txt

# Step 2: Ingest knowledge files into ChromaDB
python ingest.py

# Step 3: Search
python search.py "Jackson deserialization unknown field"
python search.py "parallel stream null pointer" --top-k 3
python search.py "redis connection pool" --level L1
python search.py "contract service error" --category service
python search.py "error pattern" --json-output
```

## Files

| File | Description |
|------|-------------|
| `rag_config.yaml` | Configuration (model, chunking, thresholds) |
| `ingest.py` | Embed and store knowledge `.md` files into ChromaDB |
| `search.py` | CLI search over the vector database |
| `requirements.txt` | Python dependencies |
| `chroma_db/` | ChromaDB persistent storage (auto-created) |

## Options

- `--full` — Full re-index (default)
- `--incremental` — Only process new/modified files
- `--top-k N` — Number of results
- `--level L1/L2/L3` — Filter by fix complexity level
- `--category fix/pattern/service` — Filter by knowledge category
- `--threshold 0.0-1.0` — Minimum similarity score
- `--json-output` — Output results as JSON

## Model

First run downloads `all-MiniLM-L6-v2` (~90MB) automatically via sentence-transformers.
