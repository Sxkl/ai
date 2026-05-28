#!/usr/bin/env python3
"""
Supabase pgvector 知识库录入 — 线上向量存储

替换本地 ChromaDB，全部数据存在 Supabase 云端。
用法:
  python ingest_pg.py          # 全量重新录入
  python ingest_pg.py --incr   # 增量更新
"""
import os
import sys
import yaml
import click
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Supabase 客户端
from supabase import create_client
from langchain_text_splitters import MarkdownHeaderTextSplitter


class SupabaseIngestor:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)

        sc = self.config["supabase"]
        self.client = create_client(sc["url"], sc["anon_key"])
        self.collection = sc["table_name"]
        self.embedding_provider = sc.get("embedding_provider", "openai")

        # 初始化 embedding API
        if self.embedding_provider == "openai":
            from openai import OpenAI
            ak = os.environ.get("OPENAI_API_KEY") or sc.get("openai_api_key", "")
            self.embed_client = OpenAI(api_key=ak)
            self.embed_model = "text-embedding-3-small"
        else:
            # 本地 SentenceTransformer 作为备用
            from sentence_transformers import SentenceTransformer
            self.embed_client = SentenceTransformer(
                self.config["embedding"]["model_name"],
                device="cpu"
            )
            self.embed_model = None

        self.splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
            strip_headers=False
        )

        self._init_table()

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path) as f:
            return yaml.safe_load(f)

    def _init_table(self):
        """创建 pgvector 表 + 索引"""
        sql = f"""
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE IF NOT EXISTS {self.collection} (
            id TEXT PRIMARY KEY,
            source_file TEXT,
            source_filename TEXT,
            chunk_index INTEGER,
            level TEXT,
            category TEXT,
            content TEXT,
            embedding vector(1536),
            file_hash TEXT,
            ingested_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        self.client.rpc("exec_sql", {"query": sql}).execute()

        # IVFFlat 索引（数据量上千后生效）
        idx_sql = f"""
        CREATE INDEX IF NOT EXISTS idx_{self.collection}_embedding
        ON {self.collection} USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """
        self.client.rpc("exec_sql", {"query": idx_sql}).execute()

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """批量向量化"""
        if self.embedding_provider == "openai":
            resp = self.embed_client.embeddings.create(
                model=self.embed_model,
                input=[t[:8000] for t in texts]
            )
            return [d.embedding for d in resp.data]
        else:
            return self.embed_client.encode(texts).tolist()

    def _file_hash(self, filepath: str) -> str:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _find_md_files(self) -> List[Path]:
        files = []
        for source in self.config["knowledge_sources"]:
            base = Path(source["path"]).expanduser()
            if not base.exists():
                print(f"WARNING: 路径不存在 {base}")
                continue
            for md_file in base.rglob(source.get("glob", "*.md")):
                if md_file.is_file():
                    files.append(md_file)
        return sorted(files)

    def _derive_level(self, path: str) -> str:
        if "/L1-" in path: return "L1"
        if "/L2-" in path: return "L2"
        if "/L3-" in path: return "L3"
        return ""

    def _derive_category(self, path: str, filename: str) -> str:
        if "/patterns/" in path: return "pattern"
        if "/services/" in path: return "service"
        if filename.startswith("K") or filename.startswith("N"): return "fix"
        if filename == "index.md": return "index"
        return "unknown"

    def ingest_all(self) -> int:
        md_files = self._find_md_files()
        print(f"找到 {len(md_files)} 个 Markdown 文件")

        # 清空旧数据
        self.client.table(self.collection).delete().neq("id", "__keep__").execute()

        all_rows = []
        for md_file in md_files:
            rel = str(md_file.relative_to(Path.home()))
            print(f"  处理: {rel}")
            content = md_file.read_text(encoding="utf-8")

            try:
                chunks = self.splitter.split_text(content)
            except Exception:
                chunks = []

            if not chunks:
                txt = content.strip()
                if len(txt) >= self.config["chunking"]["min_chunk_size"]:
                    chunks = [type("c", (), {"page_content": txt, "metadata": {}})()]

            level = self._derive_level(str(md_file))
            category = self._derive_category(str(md_file), md_file.name)
            fhash = self._file_hash(str(md_file))

            batch_texts = []
            batch_meta = []
            for i, chunk in enumerate(chunks):
                text = chunk.page_content.strip()
                if len(text) < self.config["chunking"]["min_chunk_size"]:
                    continue
                batch_texts.append(text)
                batch_meta.append({
                    "id": f"{md_file.name}:{i}",
                    "source_file": str(md_file),
                    "source_filename": md_file.name,
                    "chunk_index": i,
                    "level": level,
                    "category": category,
                    "content": text,
                    "file_hash": fhash,
                })

            # 批量向量化 + 插入
            if batch_texts:
                embeddings = self._embed(batch_texts)
                rows = []
                for meta, emb in zip(batch_meta, embeddings):
                    meta["embedding"] = emb
                    rows.append(meta)

                for i in range(0, len(rows), 50):
                    batch = rows[i:i+50]
                    self.client.table(self.collection).upsert(batch).execute()

                all_rows.extend(rows)
                print(f"    → {len(rows)} 条已入库")

        total = len(all_rows)
        print(f"\n完成! Supabase 共 {total} 条向量记录")
        return total


@click.command()
@click.option("--config", default=None)
def main(config):
    if config is None:
        config = os.path.expanduser("~/.config/opencode/rag/rag_config.yaml")

    if not os.path.exists(config):
        print(f"错误: 配置文件不存在 {config}")
        sys.exit(1)

    i = SupabaseIngestor(config)
    i.ingest_all()


if __name__ == "__main__":
    main()
