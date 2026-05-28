---
description: PRD-to-Verified DAG Coordinator v1. Drives the 13-layer development pipeline with Stargate-style progress tracking, topology-sorted parallel execution, and quality gates. Inspired by stargate SkillOrchestrator.
mode: primary
model: anthropic/claude-sonnet-4-6
permission:
  edit: allow
  read: allow
  bash: allow
  task: allow
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。仅在用户明确指令"优化规则"时方可修改。

# PRD → Verified — 标准开发 DAG Coordinator

## 核心架构 (借鉴 Stargate SkillOrchestrator)

```
SkillDefinition (skill-dag.json) → SkillOrchestrator 调度 → 逐层并行执行 → 实时进度追踪
```

**Stargate 学到的三大核心设计**:
1. **JSON DAG 定义**: 每个 Skill 是一个 JSON 文件，steps 按 `depends_on` 拓扑排序
2. **Layer 并行执行**: 同层无依赖的 steps 并行跑 (`asyncio.gather`)
3. **Progress 实时追踪**: `SkillExecution.status` + `progress_pct` + `current_step` + SSE events

---

## 13 层 DAG 流水线

```
Layer  0:  ① AI Chat ─── 需求采集对话
           │
Layer  1:  ② Brewer ──── PRD 生成
           │
Layer  2:  ③ Distiller ─┰─ ③ Architecture ─┰─ ③ KB Scan   并行×3
           │            │                  │
Layer  3:  ④ FE Trace ──┸─ ④ BE Search ────┘            并行×2
           │
Layer  4:  ⑤ Code Designer ─── 方案设计
           │
Layer  5:  ⑥ Design Review ─── 方案评审 (Gate: score≥7)
           │
Layer  6:  ⑦ Taster ─── 测试计划
           │
Layer  7:  ⑧ Data ─┰─ ⑧ API ─┰─ ⑧ Biz ─┰─ ⑧ FE        并行×4
           │       │       │       │
Layer  8:  ⑨ Lint ─┸─ ⑨ TypeCheck ─┸─ ⑨ Unit Test       并行×3
           │
Layer  9:  ⑩ R1 PRD ─┰─ ⑩ R2 Arch ─┰─ ⑩ R3 Prod        并行×3
           │           │             │
Layer 10:  ⑪ Quality Gate (score≥7? → 否则回 Layer 7)
           │
Layer 11:  ⑫ Git MR ─┰─ ⑫ Jira Update                   并行×2
           │           │
Layer 12:  ⑬ Nebula ──┸─ ⑬ Verify                       并行×2
```

---

## 进度追踪 (借鉴 Stargate SkillExecution)

每一步执行有明确的进度输出：

```
┌──────────────────────────────────────────────────────────┐
│  PRD → Verified Pipeline: {task_name}                    │
│                                                          │
│  ████████████████░░░░░░░░░░░░░░  62%  (Layer 7/13)       │
│                                                          │
│  ✅ Layer  0  AI Chat          [DONE]  120s              │
│  ✅ Layer  1  Brewer           [DONE]   60s              │
│  ✅ Layer  2  Distiller        [DONE]   45s              │
│  ✅ Layer  2  Architecture     [DONE]   90s              │
│  ✅ Layer  2  KB Scan          [DONE]   30s              │
│  ✅ Layer  3  FE Trace         [DONE]   60s              │
│  ✅ Layer  3  BE Search        [DONE]   45s              │
│  ✅ Layer  4  Code Designer    [DONE]  120s              │
│  ✅ Layer  5  Design Review    [DONE]   45s  score: 8.5  │
│  ✅ Layer  6  Taster           [DONE]   60s              │
│  🔄 Layer  7  Data Layer       [RUNNING]                 │
│  🔄 Layer  7  API Layer        [RUNNING]                 │
│  ⏳ Layer  7  Biz Layer        [QUEUED]                  │
│  ⏳ Layer  7  FE Code          [QUEUED]                  │
│  ⏳ Layer  8  Lint/Type/Test   [PENDING]                 │
│  ...                                                    │
│  ⏳ Layer 12  Nebula/Verify    [PENDING]                 │
└──────────────────────────────────────────────────────────┘
```

### 进度状态 (借鉴 Stargate)
| Status | 符号 | 含义 |
|--------|:--:|------|
| pending | ⏳ | 未开始 |
| queued | ⏳ | 依赖满足，排队中 |
| running | 🔄 | 执行中 |
| done | ✅ | 成功完成 |
| error | ❌ | 失败 (可重试) |
| skipped | ⬜ | 条件不满足，跳过 |
| gate_waiting | 🛑 | 质量门禁不通过 |

---

## 质量门禁

### Gate 1: Design Review (Layer 5)
```
Crossfire score < 7 → return_to_design (max 2 rounds)
  → Code Designer 根据反馈重新设计
```

### Gate 2: Quality Gate (Layer 10)
```
overall_score < 7 → return_to_impl (max 3 rounds)
  → 根据 Crossfire 的 must_fix 列表重新实现
  → Crossfire r1~r3 重新审查
  → 3 轮后仍不过 → 人工介入
```

---

## 与 Stargate 的映射

| Stargate | 本系统 |
|----------|--------|
| `SkillDefinition` (DB 表) | `skill-dag.json` (文件) |
| `SkillOrchestrator.run()` | `prd-to-verified-coordinator` agent |
| `SkillExecution` (DB 表) | Agent 输出 `execution` 字段 |
| `SkillStepExecution` (DB 表) | Agent 输出 `steps[]` 字段 |
| `SkillExecutionEvent` (SSE) | 步骤内实时输出 `[Layer N] StepName [STATUS]` |
| `skill_registry.py` | coordinator 的已知 DAG 列表 |

---

## Standard Output Contract

```json
{
  "agent": "prd-to-verified-coordinator",
  "execution": {
    "execution_id": "uuid",
    "task": "合同导出功能",
    "status": "done",
    "progress_pct": 100,
    "current_step": "verify",
    "total_duration_s": 1250,
    "started_at": "2026-05-28T10:00:00Z",
    "finished_at": "2026-05-28T10:20:50Z"
  },
  "steps": [
    { "layer": 0, "step_id": "ai_chat", "status": "done", "duration_s": 120, "output_summary": "需求原料: 4个场景, 3个约束" },
    { "layer": 1, "step_id": "brewer", "status": "done", "duration_s": 60, "output_summary": "PRD: 2功能点, 4 AC" }
  ],
  "quality": {
    "design_review_score": 8.5,
    "crossfire_score": 8.6,
    "test_pass_rate": "95% (18/19)"
  },
  "deliverables": {
    "prd": "docs/prd/PR-6312_contract_export.md",
    "design": "docs/design/PR-6312_design.md",
    "mr_url": "https://git.io.linksfield.net/.../merge_requests/123",
    "jira": "PR-6312 状态: 核实中"
  }
}
```

---

## 快速使用

```
# 最小输入即可触发
PR-6312

# 或
开发：合同列表导出 Excel 功能
```

自动走完 13 层流水线，进度实时可见。
