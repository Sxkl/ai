# v3.5 Release Notes — 2026-05-28

## 本次变更总览

| 维度 | 变更前 | 变更后 |
|------|--------|--------|
| Agent 数量 | 31 → 35 | **42** |
| 架构模式覆盖 | 13/21 | **20/21** |
| RAG 存储 | 本地 ChromaDB | **Supabase pgvector (云端)** |
| RAG 搜索 | 纯向量搜索 | **混合检索 (Supabase RPC)** |
| Pipeline DAG | 4 个 agent | **10 个 agent** |

---

## 新增 Agent (7)

| Agent | 模式 | 说明 |
|-------|------|------|
| `context-compressor-agent` | 上下文压缩 | 保护头尾、摘要中间，防 token 溢出 |
| `delegation-agent` | 并行委托 | ThreadPoolExecutor 子代理，任务分解→并行→聚合 |
| `mental-simulator-agent` | 内心模拟/干运行 | 执行前环境建模→推演→风险评估→决策 |
| `hybrid-search-agent` | RAG 混合检索 | BM25+向量双路召回 + Cross-Encoder 重排 |
| `cron-scheduler-agent` | 定时调度 | 自然语言定义定时任务 |
| `tree-of-thoughts-agent` | 多路径探索 | L3 复杂错误树形探索+剪枝 |
| `api-v4-auto-fix` | 10 阶段 DAG | SLS拉取→分类→匹配→根因→修复→测试→审查→部署→沉淀 |

## 升级 Agent (6)

| Agent | 旧→新 | 变化 |
|-------|:--:|------|
| `review-agent` | v3→v4 | 大文件上下文压缩 + Pipeline DAG |
| `deploy-agent` | v2→v3 | 干运行 + 安全审批门 |
| `fix-agent` | v3→v4 | 安全扫描 + 内心模拟 + Pipeline DAG |
| `memory-agent` | v1→v1.1 | 引用 SQLite+FTS5 生产实现 |
| `meta-cognitive-agent` | v1→v1.1 | 引用 security.py |
| `self-improve-agent` | v1→v1.1 | 引用 skills.py |

## Pipeline DAG 新增 (6)

| Agent | DAG 阶段 | 特性 |
|-------|:--:|------|
| `api-v4-auto-fix` | 10 | 拓扑排序 + 失败回退 + 质量门控 |
| `production-incident-fix` | 10 | git→jira→sls→db→analyze→fix→crossfire→test→deploy→report |
| `sls-log-analysis` | 7 | 并行 pattern_analyze + pattern_match |
| `crossfire` | 3 | 不同 reviewer 模型、PRD→安全→生产 |
| `decision-engine` | 3-5 | L1→L3 自适应多模型辩论 |
| `review-agent` | 5 | context→R1(P0)→R2(P1)→R3(P2)→加权评分 |

## RAG 升级

| 组件 | 变更前 | 变更后 |
|------|--------|--------|
| 向量存储 | ChromaDB 本地磁盘 | Supabase pgvector 云端 |
| 数据量 | 本地 78 chunks | Supabase 78 条 512 维向量 |
| 搜索入口 | `search.py` 本地 | `search.py` → Supabase RPC |
| 知识文件 | 20 个 MD | 同步到 Supabase |

## Prompt Caching

- 新增 `prompt-caching-guide.md`
- Claude API 自动缓存 system prompt
- 预估降本 40-55%，零代码改动

---

## 文件变更统计

```
新增文件:  15 (agent .md, rag scripts, sql, guide)
修改文件:  25 (agent 升级, rag 重写, config 更新)
删除文件:  18 (旧 api-v4-auto-fix 嵌套目录)
总变更:   ~3500 行新增, ~3000 行删除
```

## 参考

- `ai-auto-study`: https://github.com/Sxkl/ai-auto-study — 21 种 Agent 架构学习引擎
- `Hermes Agent`: https://github.com/NousResearch/hermes-agent — 生产级 AI Agent (171k stars)
