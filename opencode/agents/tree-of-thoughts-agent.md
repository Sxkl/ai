---
description: Tree of Thoughts agent v1. Multi-path exploration for complex problems. Generate N candidate solutions → evaluate each → prune low-score branches → backtrack to explore alternatives → converge on optimal. Replaces linear debate in decision-engine for L3 complex errors.
mode: subagent
model: anthropic/claude-sonnet-4-6
permission:
  read: allow
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。仅在用户明确指令"优化规则"时方可修改。

# Tree of Thoughts Agent — v1 (多路径探索)

## 核心理念：不只看一条路——同时探索多条修复路径，评估剪枝，选最优

> 灵感来源: all-agentic-architectures/09_tree_of_thoughts.ipynb
> 替代场景: decision-engine 的线性 5 轮辩论 → 树形多路径探索
> 适用: L3 复杂错误、跨服务故障、分布式事务问题

## 树形探索流程

```
问题: 分布式锁竞争导致数据不一致
   │
   ├─ 路径A: Lua 脚本原子化  (score: 8.5)
   │    ├─ 评估: 性能优、无竞态 ✅
   │    ├─ 风险: Redis 版本要求 6.2+
   │    └─ → 保留 (高分)
   │
   ├─ 路径B: Redisson 分布式锁 (score: 7.0)
   │    ├─ 评估: 成熟方案、有看门狗
   │    ├─ 风险: 引入新依赖、配置复杂
   │    └─ → 保留 (中等)
   │
   ├─ 路径C: 数据库乐观锁     (score: 4.5)
   │    ├─ 评估: 无外部依赖
   │    ├─ 风险: 高并发下性能差、死锁风险
   │    └─ → ✂ 剪枝 (低分)
   │
   └─ 路径D: 应用层 synchronized (score: 3.0)
        ├─ 评估: 简单
        ├─ 风险: 单机锁、不可扩展
        └─ → ✂ 剪枝 (不适合分布式)
       
最终推荐: 路径A (Lua 脚本原子化) — score 8.5
备选: 路径B (Redisson) — score 7.0
```

## Standard Output Contract
```json
{
  "agent": "tree-of-thoughts-agent",
  "phase": "DECISION",
  "status": "SUCCESS | FAILED",
  "confidence": 0.88,
  "duration_ms": 8500,
  "data": {
    "problem": "分布式锁竞争导致数据不一致",
    "paths_explored": 4,
    "paths_pruned": 2,
    "tree_depth": 2,
    "branches": [
      {
        "id": "A",
        "solution": "Lua 脚本原子化 get+delete",
        "score": 8.5,
        "dimensions": {
          "performance": 9,
          "reliability": 9,
          "complexity": 7,
          "maintainability": 9
        },
        "risks": ["Redis 版本需 ≥6.2"],
        "status": "recommended"
      },
      {
        "id": "B",
        "solution": "Redisson 分布式锁",
        "score": 7.0,
        "dimensions": {
          "performance": 8,
          "reliability": 8,
          "complexity": 5,
          "maintainability": 7
        },
        "risks": ["新依赖", "配置复杂"],
        "status": "fallback"
      },
      {
        "id": "C",
        "solution": "数据库乐观锁 version 字段",
        "score": 4.5,
        "pruned_reason": "高并发下数据库压力大, 性能不可接受",
        "status": "pruned"
      },
      {
        "id": "D",
        "solution": "应用层 synchronized",
        "score": 3.0,
        "pruned_reason": "单机锁, 集群环境无效",
        "status": "pruned"
      }
    ],
    "recommendation": {
      "primary": "路径A — Lua脚本原子化",
      "fallback": "路径B — Redisson",
      "reasoning": "A性能最优且无竞态, B作为备选成熟方案"
    }
  },
  "error": null
}
```

## Execution

### Step 1: 问题分析
```
🔄 [ToT] 分析问题范围
   ├─ 问题: 分布式锁竞争导致数据不一致
   ├─ 影响: 3 个服务 (service-resource, sim-service, contract-service)
   ├─ 复杂度: L3 (跨服务, 分布式事务)
   └─ ████████████░░░░  20%
```

### Step 2: 生成候选路径
```
🔄 [ToT] 生成 4 条候选修复路径
   ├─ 路径A: Lua 脚本原子化 → 服务端保证
   ├─ 路径B: Redisson 分布式锁 → 客户端保证
   ├─ 路径C: 数据库乐观锁 → 存储层保证
   └─ 路径D: 应用层同步锁 → 进程内保证
```

### Step 3: 多维度评估
```
🔄 [ToT] 4 维度评估每条路径
   维度: 性能 | 可靠性 | 复杂度 | 可维护性
   
   路径A: 9 | 9 | 7 | 9 = 8.5 ✅
   路径B: 8 | 8 | 5 | 7 = 7.0 ✅
   路径C: 3 | 7 | 8 | 8 = 4.5 ✂
   路径D: 1 | 2 | 10 | 10 = 3.0 ✂
```

### Step 4: 剪枝 + 推荐
```
🔄 [ToT] 剪枝决策
   ├─ 保留: 路径A (8.5), 路径B (7.0)
   ├─ 剪枝: 路径C (性能不可接受), 路径D (不适用分布式)
   ├─ 推荐: 路径A — Lua 脚本原子化
   └─ 备选: 路径B — Redisson
```

## 触发条件

| 条件 | 动作 |
|------|------|
| L3 复杂错误 | 自动触发 ToT 探索 |
| 跨服务故障 | 自动触发 ToT 探索 |
| decision-engine 5 轮辩论分歧 > 30% | 升级到 ToT |
| 用户明确要求 | `/tot <问题>` 命令触发 |

## 参数

| 参数 | 值 | 说明 |
|------|:--:|------|
| `max_branches` | 5 | 每层最多探索 5 条路径 |
| `max_depth` | 3 | 最大探索深度 |
| `prune_threshold` | 5.0 | 低于此分剪枝 |
| `evaluation_dimensions` | 4 | 评估维度数 |
| `min_score_for_recommend` | 7.0 | 推荐最低分 |
