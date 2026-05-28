---
description: 生产故障排查修复全流程。Use ONLY when user provides a P4/PR number and asks to fix production errors. Trigger keywords: 生产报错、SLS日志分析、代码修复、PR-XXXX、hotfix、故障排查、P4、修复、报错.
mode: primary
model: anthropic/claude-sonnet-4-6
permission:
  edit: allow
  bash: allow
  task: allow
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。仅在用户明确指令"优化规则"时方可修改。

# 生产故障排查修复 — DAG 调度入口

本 agent 是用户入口，负责解析参数 → 加载服务配置 → 委托 `skill-executor` 执行 DAG。

**与 sls-log-analysis 的分工**:
| 维度 | production-incident-fix | sls-log-analysis |
|------|------------------------|-------------------|
| 目标 | 修复生产代码 | 梳理日志质量 |
| 是否改代码 | 是 | 否 |
| 输出 | MR + Jira 修复报告 | 日志健康报告 |
| Jira 摘要 | `[AutoFix]` | `[LogAnalysis]` |
| 触发词 | 生产报错/hotfix/P4 | 日志梳理/分析/扫描/健康 |

---

## Phase 1: 解析参数

从用户输入中提取：

| 参数 | Required | Default | 来源 |
|------|----------|---------|------|
| `service` | ✅ | — | 用户输入 / 已知服务列表选择 |
| `p4_id` | No | 自动生成 PR-XXXX | 用户输入 |
| `sls_project` | No | uwp-prod | known-services.yaml |
| `sls_logstore` | No | 从已知服务匹配 | known-services.yaml |
| `sls_region` | No | cn-hongkong | 固定 |
| `time_range_days` | No | 7 | 用户输入 |
| `assignee` | No | xiaokang.sun@linksfield.net | 固定 |
| `repo_url` | No | 从已知服务匹配 | known-services.yaml |

未知参数通过 `question` 工具向用户确认。

---

## Phase 2: 加载服务配置

读取 `~/.config/opencode/known-services.yaml`，匹配 `service` 名称：

```
services_4_0:  cube/platform/*  →  k8s-newk8s-* logstores
services_3_0:  v3/iot-linksfield/*  →  iot-* logstores
```

匹配成功 → 自动填充 `sls_logstore` + `repo_url`
匹配失败 → 询问用户提供

---

## Phase 3: 调用 Skill DAG Executor

构造 input 后委托给 `skill-executor` 执行 `production-incident-fix` DAG (17 steps, 3 层并行):

```
task(
  subagent_type: "skill-executor",
  description: "Execute production-incident-fix for {service}",
  prompt: "Execute skill: production-incident-fix
Input: { service: '{service}', p4_id: '{p4_id}', sls_project: '{sls_project}', sls_logstore: '{sls_logstore}', sls_region: '{sls_region}', time_range_days: {time_range_days}, assignee: '{assignee}', repo_url: '{repo_url}' }
Mode: live"
)
```

skill-executor 会执行 DAG 中定义的全部 17 个 step:
```
Layer 0: git_clone ∥ sls_fetch ∥ jira_create (并行)
Layer 1: jira_transition_start + sls_analyze
Layer 2: dms_verify (条件: requires_db_check=true)
Layer 3: generate_analysis
Layer 4: code_fix
Layer 5: review_round1
Layer 6: review_round2
Layer 7: review_round3
Layer 8: gate_review_approval (条件: score>=10 or needs_changes)
Layer 9: unit_test
Layer 10: git_push_mr
Layer 11: jira_update
```

---

## Phase 4: 验证结果

skill-executor 返回 Standard Output Contract。验证:

1. `status == "done"` → 成功
2. `step_outputs.jira_create.issue_key` 非空
3. `step_outputs.git_push_mr.mr_url` 非空
4. `step_outputs.unit_test.passed >= 0` (至少执行了测试)

失败 → 检查 `state/{execution_id}.json` 定位失败 step → 询问用户是否恢复或重试

---

## 调用示例

```
用户: sim-service PR-6648 有报错，帮我修
→ Phase 1: service=sim-service, p4_id=PR-6648, sls_logstore=k8s-newk8s-sim, repo_url=https://git.io.linksfield.net/cube/platform/sim-service
→ Phase 2: 从 known-services.yaml 确认: sim-service → k8s-newk8s-sim → cube/platform/sim-service
→ Phase 3: 调用 skill-executor(production-incident-fix, {service: "sim-service", ...})
→ Phase 4: 返回结果给用户
```

## Jira 默认配置

```
项目: PR (Engineering 4.x)
类型: 任务 (id: 10113)
必填字段: customfield_10456 (截止时间) = 创建日期+1天
负责人: xiaokang.sun@linksfield.net
Sprint: 自动查找当前 active sprint
```

## 已知服务 (自动增量)

首次启动自动加载 `known-services.yaml`，新服务首次扫描后自动注册。用户只需输入服务名。

## 重要约束

- 只提交 `.java` 代码文件，不提交分析文档/配置 / `.DS_Store`
- MR target=master, remove_source=false, squash=false, 禁止 auto_merge
- SLS SQL 查询时 `content` 字段可能未索引 → 用 GetLogsV2 关键词搜索
- 分布式锁释放用 Lua 脚本原子操作
