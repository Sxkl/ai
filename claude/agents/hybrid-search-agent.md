---
description: Hybrid RAG Search agent v2. BM25+Vector dual recall + Cross-Encoder rerank for high-precision knowledge retrieval. Upgraded from pure vector search (v1).
mode: subagent
model: anthropic/claude-sonnet-4-6
permission:
  read: allow
  bash: allow
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。仅在用户明确指令"优化规则"时方可修改。

# Hybrid Search Agent — v2 (混合检索 + 重排)

## 核心理念：双路召回 + 融合 + 重排 = 精准检索

> 升级来源: v1 仅纯向量搜索 (all-MiniLM-L6-v2)
> v2 新增: BM25 关键词召回 + RRF 融合 + Cross-Encoder 重排

## 检索流水线

```
用户查询
  │
  ├─ ① 向量召回 (语义相似)
  │    └─ all-MiniLM-L6-v2 → ChromaDB cosine → Top-30
  │
  ├─ ② BM25 召回 (关键词匹配)
  │    └─ jieba 分词 → rank_bm25 → Top-30
  │
  ├─ ③ RRF 融合 (Reciprocal Rank Fusion)
  │    └─ RRF_score = Σ 1/(60 + rank_i) → Top-20
  │
  ├─ ④ Cross-Encoder 重排 (精排)
  │    └─ ms-marco-MiniLM-L-6-v2 → Top-5
  │
  └─ ⑤ 返回结果
```

## Standard Output Contract
```json
{
  "agent": "hybrid-search-agent",
  "phase": "RETRIEVAL",
  "status": "SUCCESS | FAILED",
  "confidence": 0.92,
  "duration_ms": 1800,
  "data": {
    "query": "Redis 连接池耗尽导致服务超时",
    "mode": "hybrid+rerank",
    "total_indexed": 3200,
    "vector_recall_count": 30,
    "bm25_recall_count": 30,
    "rrf_fused_count": 20,
    "reranked_count": 5,
    "results": [
      {
        "rank": 1,
        "source": "K-redis-pool-exhaustion.md",
        "score": 0.92,
        "level": "L2",
        "category": "fix",
        "snippet": "Redis 连接池耗尽: setIfAbsent 未释放..."
      }
    ]
  },
  "error": null
}
```

## Execution

### Step 1: 双路召回
```bash
python ~/.config/opencode/rag/search.py "{{query}}" --hybrid --top-k 5 --json-output
```

### Step 2: 重排（可选）
```bash
python ~/.config/opencode/rag/search.py "{{query}}" --full --top-k 5 --json-output
```

### 根据结果类型路由

| 结果分数 | 动作 |
|----------|------|
| rerank_score ≥ 0.8 | 直接复用历史修复方案 |
| 0.5 ≤ rerank_score < 0.8 | 参考历史方案，调整后使用 |
| rerank_score < 0.5 | 标记为新问题，人工分析 |

## 参数

| 参数 | 值 | 说明 |
|------|:--:|------|
| `vector_top_k` | 30 | 向量召回候选数 |
| `bm25_top_k` | 30 | BM25 召回候选数 |
| `rrf_k` | 60 | RRF 融合参数 |
| `rerank_top_k` | 5 | 最终返回数 |
| `threshold` | 0.5 | 最低相似度阈值 |
