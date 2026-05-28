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

### Pipeline DAG（必须按此拓扑执行）

```yaml
pipeline:
  max_parallel: 3
  on_failure: return_to_previous

  stages:
    - stage: 1
      id: sls_pull
      agent: sls-agent
      depends_on: []
      timeout: 120s
      on_fail: RETRY_ONCE

    - stage: 2
      id: log_classify
      agent: analyze-agent
      depends_on: [sls_pull]
      prompt: "分类以下日志: ${sls_pull.output}"
      timeout: 60s

    - stage: 3
      id: pattern_match
      agent: hybrid-search-agent
      depends_on: [log_classify]
      command: "python ~/.config/opencode/rag/search.py '${log_classify.output.top_errors}' --top-k 5"
      timeout: 30s

    - stage: 4
      id: root_cause
      agent: analyze-agent
      depends_on: [log_classify, pattern_match]
      prompt: "基于分类结果和匹配模式分析根因: ${log_classify.output} + ${pattern_match.output}"
      timeout: 90s

    - stage: 5
      id: code_fix
      agent: fix-agent
      depends_on: [root_cause]
      prompt: "修复以下根因: ${root_cause.output}"
      timeout: 180s

    - stage: 6
      id: run_tests
      agent: test-agent
      depends_on: [code_fix]
      timeout: 120s
      on_fail: RETURN_TO_STAGE_5

    - stage: 7
      id: code_review
      agent: review-agent
      depends_on: [run_tests]
      timeout: 120s
      quality_gate: score >= 7

    - stage: 8
      id: jira_update
      agent: jira-agent
      depends_on: [code_review]
      timeout: 60s

    - stage: 9
      id: deploy
      agent: deploy-agent
      depends_on: [code_review, jira_update]
      timeout: 120s
      gate: review_score >= 7

    - stage: 10
      id: knowledge_deposit
      agent: nebula
      depends_on: [deploy]
      timeout: 60s
```

### 各阶段详情

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
