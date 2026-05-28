#!/usr/bin/env python3
"""
RAG Knowledge Base Ingestion Script

Usage:
  python ingest.py          # Full re-index (default)
  python ingest.py --full   # Full re-index
  python ingest.py --incremental  # Only process new/modified files
"""
import os
import sys
import hashlib
import yaml
import chromadb
import click
from pathlib import Path
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import MarkdownHeaderTextSplitter
from datetime import datetime


class KnowledgeIngestor:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)

        persist_dir = Path(self.config["chromadb"]["persist_directory"]).expanduser()
        persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=self.config["chromadb"]["collection_name"],
            metadata={"hnsw:space": "cosine"}
        )

        model_name = self.config["embedding"]["model_name"]
        print(f"Loading embedding model: {model_name} ...")
        self.embedder = SentenceTransformer(
            model_name,
            device=self.config["embedding"]["device"]
        )
        print(f"  Model loaded. Dimension: {self.embedder.get_sentence_embedding_dimension()}")

        self.splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
            strip_headers=False
        )

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path) as f:
            return yaml.safe_load(f)

    def _file_hash(self, filepath: str) -> str:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _find_md_files(self) -> List[Path]:
        files = []
        for source in self.config["knowledge_sources"]:
            base = Path(source["path"]).expanduser()
            if not base.exists():
                print(f"WARNING: Source path not found: {base}")
                continue
            for md_file in base.rglob(source.get("glob", "*.md")):
                if md_file.is_file():
                    files.append(md_file)
        return sorted(files)

    def _derive_level(self, rel_path: str) -> str:
        if "/L1-" in rel_path:
            return "L1"
        elif "/L2-" in rel_path:
            return "L2"
        elif "/L3-" in rel_path:
            return "L3"
        return ""

    def _derive_category(self, rel_path: str, filename: str) -> str:
        if "/patterns/" in rel_path:
            return "pattern"
        elif "/services/" in rel_path:
            return "service"
        elif filename.startswith("K") or filename.startswith("N"):
            return "fix"
        elif filename == "index.md":
            return "index"
        return "unknown"

    def _chunk_document(self, content: str, filepath: Path) -> List[Dict]:
        chunks = []
        try:
            doc_chunks = self.splitter.split_text(content)
        except Exception:
            doc_chunks = []

        if not doc_chunks:
            text = content.strip()
            if len(text) >= self.config["chunking"]["min_chunk_size"]:
                doc_chunks = [type("obj", (object,), {"page_content": text, "metadata": {}})()]

        rel_path = str(filepath)
        filename = filepath.name
        level = self._derive_level(rel_path)
        category = self._derive_category(rel_path, filename)
        file_hash = self._file_hash(str(filepath))

        for i, chunk in enumerate(doc_chunks):
            text = chunk.page_content.strip()
            if len(text) < self.config["chunking"]["min_chunk_size"]:
                continue

            chunk_id = f"{filename}:{i}"
            metadata = {
                "source_file": str(filepath),
                "source_filename": filename,
                "chunk_index": i,
                "ingested_at": datetime.now().isoformat(),
                "file_hash": file_hash,
            }
            if level:
                metadata["level"] = level
            if category:
                metadata["category"] = category

            chunks.append({
                "text": text,
                "id": chunk_id,
                "metadata": metadata
            })

        return chunks

    def ingest_all(self) -> int:
        md_files = self._find_md_files()
        print(f"Found {len(md_files)} markdown files")

        all_chunks = []
        for md_file in md_files:
            rel_path = str(md_file.relative_to(Path.home()))
            print(f"  Processing: {rel_path}")
            content = md_file.read_text(encoding="utf-8")
            chunks = self._chunk_document(content, md_file)
            all_chunks.extend(chunks)
            print(f"    -> {len(chunks)} chunks")

        if not all_chunks:
            print("No chunks generated. Check your files.")
            return 0

        try:
            existing_ids = self.collection.get()["ids"]
            if existing_ids:
                self.collection.delete(ids=existing_ids)
        except Exception:
            pass

        texts = [c["text"] for c in all_chunks]
        ids = [c["id"] for c in all_chunks]
        metadatas = [c["metadata"] for c in all_chunks]

        print(f"\nEmbedding {len(texts)} chunks ...")
        embeddings = self.embedder.encode(texts, show_progress_bar=True)

        print(f"Storing to ChromaDB ...")
        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            end = min(i + batch_size, len(all_chunks))
            self.collection.add(
                embeddings=embeddings[i:end].tolist(),
                documents=texts[i:end],
                ids=ids[i:end],
                metadatas=metadatas[i:end]
            )

        print(f"\nDone. Total chunks in DB: {self.collection.count()}")
        return len(all_chunks)

    def ingest_incremental(self) -> int:
        md_files = self._find_md_files()
        new_count = 0

        for md_file in md_files:
            file_hash = self._file_hash(str(md_file))

            try:
                existing = self.collection.get(
                    where={"source_file": str(md_file)},
                    limit=1
                )
            except Exception:
                existing = {"ids": [], "metadatas": []}

            if existing["ids"] and existing["metadatas"]:
                stored_hash = existing["metadatas"][0].get("file_hash")
                if stored_hash == file_hash:
                    continue

            if existing["ids"]:
                old_ids = self.collection.get(
                    where={"source_file": str(md_file)}
                )["ids"]
                if old_ids:
                    self.collection.delete(ids=old_ids)

            content = md_file.read_text(encoding="utf-8")
            chunks = self._chunk_document(content, md_file)

            if chunks:
                texts = [c["text"] for c in chunks]
                ids = [c["id"] for c in chunks]
                metadatas = [c["metadata"] for c in chunks]

                embeddings = self.embedder.encode(texts)
                self.collection.add(
                    embeddings=embeddings.tolist(),
                    documents=texts,
                    ids=ids,
                    metadatas=metadatas
                )
                new_count += len(chunks)
                rel_path = str(md_file.relative_to(Path.home()))
                print(f"  Updated: {rel_path} -> {len(chunks)} chunks")

        return new_count


@click.command()
@click.option("--config", default=None, help="Path to rag_config.yaml")
@click.option("--full", is_flag=True, help="Full re-index")
@click.option("--incremental", is_flag=True, help="Incremental update (new/modified files only)")
def main(config, full, incremental):
    if config is None:
        config = os.path.expanduser("~/.config/opencode/rag/rag_config.yaml")

    if not os.path.exists(config):
        print(f"ERROR: Config file not found: {config}")
        sys.exit(1)

    ingestor = KnowledgeIngestor(config)

    if incremental:
        count = ingestor.ingest_incremental()
        print(f"\nIncremental ingest complete: {count} new/updated chunks")
    else:
        count = ingestor.ingest_all()
        print(f"\nIngest complete: {count} chunks")


if __name__ == "__main__":
    main()
