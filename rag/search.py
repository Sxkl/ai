#!/usr/bin/env python3
"""
RAG Knowledge Base Search CLI

Usage:
  python search.py "error description"
  python search.py "query" --top-k 10
  python search.py "query" --level L1
  python search.py "query" --category pattern
  python search.py "query" --json-output
"""
import os
import sys
import json
import yaml
import chromadb
import click
from pathlib import Path
from sentence_transformers import SentenceTransformer


class RAGSearch:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)

        persist_dir = Path(self.config["chromadb"]["persist_directory"]).expanduser()
        if not persist_dir.exists():
            print(f"ERROR: ChromaDB not found at {persist_dir}")
            print("Run 'python ingest.py' first.")
            sys.exit(1)

        self.client = chromadb.PersistentClient(path=str(persist_dir))
        try:
            self.collection = self.client.get_collection(
                name=self.config["chromadb"]["collection_name"]
            )
        except Exception:
            print(f"ERROR: Collection '{self.config['chromadb']['collection_name']}' not found.")
            print("Run 'python ingest.py' first.")
            sys.exit(1)

        model_name = self.config["embedding"]["model_name"]
        self.embedder = SentenceTransformer(
            model_name,
            device=self.config["embedding"]["device"]
        )

    def _load_config(self, config_path: str) -> dict:
        with open(config_path) as f:
            return yaml.safe_load(f)

    def search(self, query: str, top_k: int = 5,
               level: str = None, category: str = None,
               threshold: float = None) -> list:
        if threshold is None:
            threshold = self.config["search"]["similarity_threshold"]

        query_embedding = self.embedder.encode([query])

        where_filter = {}
        if level:
            where_filter["level"] = level
        if category:
            where_filter["category"] = category

        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )

        hits = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                similarity = 1 - results["distances"][0][i]
                if similarity < threshold:
                    continue
                meta = results["metadatas"][0][i]
                hits.append({
                    "rank": i + 1,
                    "score": round(similarity, 4),
                    "knowledge_id": results["ids"][0][i],
                    "source": meta.get("source_filename", meta.get("source_file", "")),
                    "level": meta.get("level", ""),
                    "category": meta.get("category", ""),
                    "text": results["documents"][0][i][:500],
                })

        return hits

    def get_stats(self) -> dict:
        return {
            "collection": self.collection.name,
            "total_chunks": self.collection.count(),
        }


@click.command()
@click.argument("query")
@click.option("--top-k", default=5, help="Number of results (default: 5)")
@click.option("--level", default=None, help="Filter by level (L1/L2/L3)")
@click.option("--category", default=None, help="Filter by category (fix/pattern/service)")
@click.option("--threshold", default=None, type=float, help="Similarity threshold (default: 0.5)")
@click.option("--json-output", is_flag=True, help="Output as JSON")
@click.option("--config", default=None, help="Path to rag_config.yaml")
def main(query, top_k, level, category, threshold, json_output, config):
    if config is None:
        config = os.path.expanduser("~/.config/opencode/rag/rag_config.yaml")

    if not os.path.exists(config):
        print(f"ERROR: Config file not found: {config}")
        sys.exit(1)

    searcher = RAGSearch(config)
    results = searcher.search(query, top_k, level, category, threshold)

    if json_output:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    if not results:
        print(f'No results found for: "{query}"')
        if level:
            print(f"(level filter: {level})")
        if category:
            print(f"(category filter: {category})")
        return

    print(f'\nQuery: "{query}"')
    print(f"Found {len(results)} results:\n")
    print("-" * 70)
    for hit in results:
        source = hit["source"]
        print(f"[{hit['rank']}] {source}")
        print(f"    Knowledge ID: {hit['knowledge_id']}")
        print(f"    Score: {hit['score']} | Level: {hit['level']} | Category: {hit['category']}")
        snippet = hit["text"][:200].replace("\n", " ")
        print(f"    Summary: {snippet}...")
        print("-" * 70)


if __name__ == "__main__":
    main()
