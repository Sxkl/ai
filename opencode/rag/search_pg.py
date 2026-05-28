#!/usr/bin/env python3
"""
Supabase pgvector 向量搜索 — 线上 RAG 检索

用法:
  python search_pg.py "查询内容"
  python search_pg.py "查询" --top-k 10 --json
"""
import os
import sys
import json
import yaml
import click
from typing import List
from supabase import create_client


class SupabaseSearch:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        sc = self.config["supabase"]
        self.client = create_client(sc["url"], sc["anon_key"])
        self.table = sc["table_name"]
        self.embedding_provider = sc.get("embedding_provider", "openai")

        if self.embedding_provider == "openai":
            from openai import OpenAI
            ak = os.environ.get("OPENAI_API_KEY") or sc.get("openai_api_key", "")
            self.embed_client = OpenAI(api_key=ak)
            self.embed_model = "text-embedding-3-small"
        else:
            from sentence_transformers import SentenceTransformer
            self.embed_client = SentenceTransformer(
                self.config["embedding"]["model_name"], device="cpu"
            )
            self.embed_model = None

    def _load_config(self, config_path: str) -> dict:
        with open(config_path) as f:
            return yaml.safe_load(f)

    def _embed(self, text: str) -> List[float]:
        if self.embedding_provider == "openai":
            resp = self.embed_client.embeddings.create(
                model=self.embed_model, input=text[:8000]
            )
            return resp.data[0].embedding
        else:
            return self.embed_client.encode([text]).tolist()[0]

    def search(self, query: str, top_k: int = 5,
               level: str = None, category: str = None,
               threshold: float = 0.4) -> List[dict]:
        query_vec = self._embed(query)

        # 用 RPC 调用 pgvector 的余弦相似度搜索
        rpc_params = {
            "query_embedding": query_vec,
            "match_count": top_k,
            "similarity_threshold": threshold,
        }
        if level:
            rpc_params["filter_level"] = level
        if category:
            rpc_params["filter_category"] = category

        # 需要先创建搜索 RPC 函数
        result = self.client.rpc("search_knowledge", rpc_params).execute()

        hits = []
        if result.data:
            for i, row in enumerate(result.data):
                hits.append({
                    "rank": i + 1,
                    "score": round(row.get("similarity", 0), 4),
                    "source": row.get("source_filename", ""),
                    "level": row.get("level", ""),
                    "category": row.get("category", ""),
                    "text": (row.get("content", "") or "")[:500],
                })
        return hits

    def init_search_rpc(self):
        """创建 pgvector 搜索存储过程（首次运行需要）"""
        sql = f"""
        CREATE OR REPLACE FUNCTION search_knowledge(
            query_embedding vector(1536),
            match_count INT DEFAULT 5,
            similarity_threshold FLOAT DEFAULT 0.4,
            filter_level TEXT DEFAULT NULL,
            filter_category TEXT DEFAULT NULL
        )
        RETURNS TABLE(
            id TEXT,
            source_filename TEXT,
            level TEXT,
            category TEXT,
            content TEXT,
            similarity FLOAT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT
                k.id,
                k.source_filename,
                k.level,
                k.category,
                k.content,
                1 - (k.embedding <=> query_embedding) AS similarity
            FROM {self.table} k
            WHERE 1 - (k.embedding <=> query_embedding) > similarity_threshold
              AND (filter_level IS NULL OR k.level = filter_level)
              AND (filter_category IS NULL OR k.category = filter_category)
            ORDER BY k.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$;
        """
        self.client.rpc("exec_sql", {"query": sql}).execute()
        print("RPC search_knowledge 创建完成")


@click.command()
@click.argument("query")
@click.option("--top-k", default=5)
@click.option("--level", default=None)
@click.option("--category", default=None)
@click.option("--json-output", is_flag=True)
@click.option("--init", is_flag=True, help="初始化 RPC 函数")
@click.option("--config", default=None)
def main(query, top_k, level, category, json_output, init, config):
    if config is None:
        config = os.path.expanduser("~/.config/opencode/rag/rag_config.yaml")

    s = SupabaseSearch(config)

    if init:
        s.init_search_rpc()
        return

    results = s.search(query, top_k, level, category)

    if json_output:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    print(f'\n查询: "{query}"')
    print(f"结果: {len(results)} 条\n" + "-" * 60)
    for hit in results:
        print(f"[{hit['rank']}] {hit['source']}  ({hit['score']:.4f})")
        print(f"    {hit['text'][:150]}...")
        print("-" * 60)


if __name__ == "__main__":
    main()
