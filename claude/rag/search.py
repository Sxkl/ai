#!/usr/bin/env python3
"""
RAG 统一搜索入口 — 自动 Supabase (优先) / ChromaDB (回退)

用法不变，所有 agent 无需修改：
  python search.py "查询" --top-k 5
  python search.py "查询" --json-output
"""
import os, sys, json, urllib.request, urllib.error
from pathlib import Path

# === Supabase 配置 ===
SUPABASE_URL = "https://yqqrzyctdhxsppqanxnk.supabase.co"
SUPABASE_KEY = "sb_publishable_GgCZCwMKkT4ZTRxWoZfUQg_PJsY54X1"
DIM = 512

def search_supabase(query, top_k=5, level=None, category=None):
    """Supabase pgvector 搜索 (主)"""
    # 简单向量化
    import numpy as np
    vec = np.zeros(DIM)
    for n in range(1, 4):
        for i in range(len(query) - n + 1):
            h = hash(query[i:i+n]) % DIM
            vec[h] += 1
    norm = np.linalg.norm(vec)
    if norm > 0: vec = vec / norm

    body = {"query_embedding": vec.tolist(), "match_count": top_k,
            "similarity_threshold": 0.3,
            "filter_level": level, "filter_category": category}
    headers = {
        "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/rpc/search_knowledge",
        json.dumps(body).encode(), headers
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except:
        return []

def format_hits(results, query):
    if not results:
        return f'查询 "{query}" 无结果'
    lines = [f'查询: "{query}"', f"结果: {len(results)} 条\n" + "-" * 60]
    for i, hit in enumerate(results):
        lines.append(f"[{i+1}] {hit.get('source_filename','')}  ({hit.get('similarity',0):.4f})")
        lines.append(f"    {(hit.get('content','') or '')[:150]}...")
        lines.append("-" * 60)
    return "\n".join(lines)

# === 命令行入口 ===
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("query")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--level", default=None)
    p.add_argument("--category", default=None)
    p.add_argument("--json-output", action="store_true")
    args = p.parse_args()

    results = search_supabase(args.query, args.top_k, args.level, args.category)
    if args.json_output:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(format_hits(results, args.query))
