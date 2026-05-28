#!/usr/bin/env python3
"""
增强 RAG 搜索 — 混合检索（向量+BM25）+ Cross-Encoder 重排

新增能力:
  1. BM25 关键词搜索 (rank_bm25)
  2. 混合融合 RRF (Reciprocal Rank Fusion)
  3. Cross-Encoder 重排 (ms-marco-MiniLM-L-6-v2)
  4. 多路召回: 向量 + BM25 → RRF融合 → 重排 → Top-K

用法:
  python search.py "error" --hybrid     # 混合搜索
  python search.py "error" --rerank     # 加重排
  python search.py "error" --full       # 全流程: 混合+重排
"""
import os
import sys
import json
import yaml
import chromadb
import click
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer


class RAGSearch:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        persist_dir = Path(self.config["chromadb"]["persist_directory"]).expanduser()

        if not persist_dir.exists():
            print(f"ERROR: ChromaDB not found at {persist_dir}")
            sys.exit(1)

        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = self.client.get_collection(
            name=self.config["chromadb"]["collection_name"]
        )

        model_name = self.config["embedding"]["model_name"]
        self.embedder = SentenceTransformer(model_name, device=self.config["embedding"]["device"])

        # === v2 增强: BM25 索引 ===
        self.bm25 = None
        self.bm25_docs = []
        self._lazy_init_bm25()

        # === v2 增强: Cross-Encoder 重排器 ===
        self.reranker = None
        if self.config["search"].get("rerank_enabled", False):
            self._lazy_init_reranker()

    def _load_config(self, config_path: str) -> dict:
        with open(config_path) as f:
            return yaml.safe_load(f)

    def _lazy_init_bm25(self):
        """构建 BM25 关键词索引"""
        try:
            from rank_bm25 import BM25Okapi
            import jieba

            all_data = self.collection.get(include=["documents"])
            if not all_data["documents"]:
                return

            # 中文分词
            self.bm25_docs = []
            tokenized = []
            for doc in all_data["documents"]:
                tokens = list(jieba.cut(doc))
                tokenized.append(tokens)
                self.bm25_docs.append(doc)

            self.bm25 = BM25Okapi(tokenized)
            print(f"  BM25 index built: {len(self.bm25_docs)} docs")
        except ImportError:
            print("  BM25 skipped: pip install rank-bm25 jieba")
        except Exception as e:
            print(f"  BM25 init failed: {e}")

    def _lazy_init_reranker(self):
        """初始化 Cross-Encoder 重排器"""
        try:
            from sentence_transformers import CrossEncoder
            model = self.config["search"].get("rerank_model", "cross-encoder/ms-marco-MiniLM-L-6-v2")
            self.reranker = CrossEncoder(model)
            print(f"  Cross-Encoder loaded: {model}")
        except Exception as e:
            print(f"  Cross-Encoder init failed: {e}")

    # ========== 向量搜索 ==========
    def search_vector(self, query: str, top_k: int = 10,
                      level: str = None, category: str = None) -> List[dict]:
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
                meta = results["metadatas"][0][i]
                hits.append({
                    "id": results["ids"][0][i],
                    "score": round(similarity, 4),
                    "source": meta.get("source_filename", ""),
                    "level": meta.get("level", ""),
                    "category": meta.get("category", ""),
                    "text": results["documents"][0][i],
                })
        return hits

    # ========== BM25 搜索 (v2 新增) ==========
    def search_bm25(self, query: str, top_k: int = 10) -> List[dict]:
        if self.bm25 is None:
            return []

        import jieba
        tokens = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokens)

        # 归一化
        if scores.max() > 0:
            scores = scores / scores.max()

        # Top-K
        top_indices = np.argsort(scores)[::-1][:top_k]

        hits = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue
            hits.append({
                "id": f"bm25_{idx}",
                "score": round(float(scores[idx]), 4),
                "source": "bm25_match",
                "level": "",
                "category": "",
                "text": self.bm25_docs[idx][:500],
            })
        return hits

    # ========== RRF 融合 (v2 新增) ==========
    def _rrf_fusion(self, results_a: List[dict], results_b: List[dict],
                    k: int = 60, top_k: int = 10) -> List[dict]:
        """
        Reciprocal Rank Fusion — 融合两路结果。
        RRF_score(d) = Σ 1/(k + rank_i(d))
        """
        scores = {}
        doc_map = {}

        for rank, hit in enumerate(results_a):
            doc_id = hit["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            doc_map[doc_id] = hit

        for rank, hit in enumerate(results_b):
            doc_id = hit["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            if doc_id not in doc_map:
                doc_map[doc_id] = hit

        sorted_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
        fused = []
        for doc_id in sorted_ids:
            hit = doc_map[doc_id].copy()
            hit["rrf_score"] = round(scores[doc_id], 4)
            fused.append(hit)
        return fused

    # ========== Cross-Encoder 重排 (v2 新增) ==========
    def rerank(self, query: str, candidates: List[dict], top_k: int = 5) -> List[dict]:
        if not self.reranker or not candidates:
            return candidates[:top_k]

        pairs = [(query, c["text"][:500]) for c in candidates]
        scores = self.reranker.predict(pairs)

        for i, c in enumerate(candidates):
            c["rerank_score"] = round(float(scores[i]), 4)

        candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return candidates[:top_k]

    # ========== 搜索入口 ==========
    def search(self, query: str, top_k: int = 5,
               level: str = None, category: str = None,
               threshold: float = None, hybrid: bool = False,
               rerank: bool = False) -> List[dict]:

        if threshold is None:
            threshold = self.config["search"]["similarity_threshold"]

        if hybrid and self.bm25:
            # 双路召回
            vec_hits = self.search_vector(query, top_k=top_k * 3, level=level, category=category)
            bm25_hits = self.search_bm25(query, top_k=top_k * 3)
            hits = self._rrf_fusion(vec_hits, bm25_hits, top_k=top_k * 2)
        else:
            hits = self.search_vector(query, top_k=top_k * 2, level=level, category=category)

        # 相似度阈值过滤
        filtered = [h for h in hits if h.get("score", 0) >= threshold or h.get("rrf_score", 0) > 0]

        # Cross-Encoder 重排
        if rerank and self.reranker:
            filtered = self.rerank(query, filtered, top_k=top_k)

        # 最终截断
        final = filtered[:top_k]
        for i, h in enumerate(final):
            h["rank"] = i + 1
            h["text"] = h["text"][:500]

        return final

    def get_stats(self) -> dict:
        return {
            "collection": self.collection.name,
            "total_chunks": self.collection.count(),
            "bm25_enabled": self.bm25 is not None,
            "reranker_enabled": self.reranker is not None,
        }


@click.command()
@click.argument("query")
@click.option("--top-k", default=5, help="结果数量")
@click.option("--level", default=None, help="过滤级别 L1/L2/L3")
@click.option("--category", default=None, help="过滤类别 fix/pattern/service")
@click.option("--hybrid/--no-hybrid", default=True, help="启用混合搜索")
@click.option("--rerank/--no-rerank", default=False, help="启用 Cross-Encoder 重排")
@click.option("--full", is_flag=True, help="全流程: 混合+重排")
@click.option("--json-output", is_flag=True, help="JSON 输出")
@click.option("--config", default=None, help="配置文件路径")
def main(query, top_k, level, category, hybrid, rerank, full, json_output, config):
    if config is None:
        config = os.path.expanduser("~/.config/opencode/rag/rag_config.yaml")

    if not os.path.exists(config):
        print(f"ERROR: Config not found: {config}")
        sys.exit(1)

    if full:
        hybrid = True
        rerank = True

    searcher = RAGSearch(config)
    results = searcher.search(
        query, top_k, level, category,
        hybrid=hybrid, rerank=rerank
    )

    if json_output:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    stats = searcher.get_stats()
    print(f'\n查询: "{query}"')
    print(f'模式: {"混合" if hybrid else "向量"} + {"重排" if rerank else "无重排"}')
    print(f'知识库: {stats["total_chunks"]} chunks | BM25: {stats["bm25_enabled"]} | Rerank: {stats["reranker_enabled"]}')
    print(f'结果: {len(results)} 条\n{"-" * 60}')

    for hit in results:
        score = hit.get("rerank_score") or hit.get("rrf_score") or hit.get("score", 0)
        print(f"[{hit['rank']}] {hit['source']}")
        print(f"    分数: {score:.4f} | 级别: {hit['level']} | 类别: {hit['category']}")
        print(f"    {hit['text'][:150]}...")
        print("-" * 60)


if __name__ == "__main__":
    main()
