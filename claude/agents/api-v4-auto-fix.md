---
description: API v4 Auto-Fix v2. 10-stage DAG pipeline: SLS log pull → classification → pattern matching → root cause → fix → test → deploy. Full automated production incident resolution.
mode: primary
model: anthropic/claude-sonnet-4-6
permission:
  read: allow
  bash: allow
  edit: allow
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。仅在用户明确指令"优化规则"时方可修改。

# API v4 Auto-Fix Agent — v2 (生产故障自动修复 DAG)

## 核心流水线

```
SLS拉取 → 日志分类 → 模式匹配 → 根因分析 → 代码修复 → 测试 → 审查 → Jira → Deploy → 知识沉淀
  ①         ②         ③          ④          ⑤        ⑥      ⑦       ⑧      ⑨        ⑩
```

## Standard Output Contract
```json
{
  "agent": "api-v4-auto-fix",
  "phase": "AUTO_FIX",
  "stage": 3,
  "status": "SUCCESS | FAILED",
  "confidence": 0.92,
  "data": {
    "service": "cube-api-v4",
    "total_errors": 156,
    "classified": {"NPE": 45, "timeout": 32, "serialize": 28, "connection": 18, "unknown": 33},
    "patterns_matched": 3,
    "root_cause": "Jackson 反序列化未知字段 + Redis 连接池耗尽 + Feign 超时无兜底",
    "files_fixed": 5,
    "test_pass_rate": 1.0,
    "review_score": 8.2,
    "jira": "PROJ-6684",
    "mr_url": "https://git.io.linksfield.net/.../merge_requests/..."
  }
}
```

## Execution — 10 阶段

### ① SLS 拉取 (delegate → sls-agent)
```
拉取 cube-api-v4 最近 24h ERROR 日志
```

### ② 日志分类 (delegate → log-classifier)
```
将错误分为: NPE / timeout / serialize / connection / unknown 5 类
```

### ③ 模式匹配 (Supabase RAG)
```bash
python ~/.config/opencode/rag/search.py "错误关键词" --top-k 5 --json-output
```
检索 Supabase 知识库中类似问题的修复模式

### ④ 根因分析 (delegate → analyze-agent)
```
基于分类结果 + 匹配模式, 分析根因
```

### ⑤ 代码修复 (delegate → fix-agent)
```
应用修复方案, 每个文件 before/after diff
```

### ⑥ 测试 (delegate → test-agent)
```
运行单元测试, 验证修复
```

### ⑦ 审查 (delegate → review-agent)
```
3 轮审查 + 评分
```

### ⑧ Jira 回写 (delegate → jira-agent)
```
创建 Jira + 回写分析报告
```

### ⑨ 部署 (delegate → deploy-agent)
```
git commit + push + MR 创建
```

### ⑩ 知识沉淀 (delegate → nebula)
```
将本次修复模式写入 knowledge/ 目录
```

## 噪声过滤

| 模式 | 过滤原因 |
|------|---------|
| `connection reset by peer` | 客户端断开, 非服务端错误 |
| `Broken pipe` | 客户端超时断开 |
| `context deadline exceeded` | gRPC 超时 |
| 心跳/健康检查错误 | 运维探测 |

## Pre-Scan 匹配

部署前先扫描 Supabase 知识库中历史相似错误:
```bash
python ~/.config/opencode/rag/search.py "Jackson 反序列化 Redis 连接 Feign" --top-k 5
```
