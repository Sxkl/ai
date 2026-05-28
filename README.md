# OpenCode Multi-Agent System

[![Agents](https://img.shields.io/badge/Agents-31-blue)](./opencode/agents/)
[![Skills](https://img.shields.io/badge/Skills-26-green)](./opencode/skills/)
[![DAGs](https://img.shields.io/badge/DAGs-4-orange)](./opencode/skills/)
[![Lines](https://img.shields.io/badge/Lines-102K-lightgrey)]()
[![Status](https://img.shields.io/badge/Status-Production-brightgreen)]()

基于 [OpenCode](https://opencode.ai) 的生产级多 Agent 协作平台，**31 个 Agent + 26 个 Skill + 4 套 DAG 流水线**，覆盖 Bug 修复、全栈开发、Continuous Loop 全流程。两套**独立副本**（`opencode/` / `claude/`）各自演化、相互学习。

---

## 三流水线架构

```
┌─────────────────────────────────────────────────────────────┐
│                     OpenCode Agent System                     │
│                       31 Agents · 102K 行                      │
├─────────────────┬─────────────────┬─────────────────────────┤
│  修复流水线       │  开发流水线       │  Continuous Loop        │
│  (coordinator)   │  (dev-harness)   │  (continuous-loop)      │
│  生产故障排查      │  全栈 Harness DAG │  8 阶段闭环开发          │
│  → Bug Fix       │  → Feature Dev   │  → PRD → Verify ↻       │
├─────────────────┼─────────────────┼─────────────────────────┤
│  DAG Skills                                │                 │
│  ├─ production-incident-fix   (17 步)       │                 │
│  ├─ code-review               (10 步)       │                 │
│  ├─ sls-log-analysis          (12 步)       │                 │
│  └─ prd-to-verified           (24 步)       │                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
├── opencode/                          ← ~/.config/opencode/
│   ├── agents/      31 agents · 102K 行
│   ├── skills/      26 skills · 4 DAG
│   ├── knowledge/   19 模式 + 3 SOP + 2 服务文档
│   ├── rag/         ChromaDB 向量检索
│   └── opencode.json
│
├── claude/                             ← ~/.claude/ 独立副本
│   ├── agents/      同 opencode
│   ├── skills/      同 opencode
│   ├── knowledge/   同 opencode
│   └── CLAUDE.md
│
└── agentic-architectures-analysis.md   ← 17 种架构学习报告
```

---

## Agent 清单 (31)

### 修复流水线 (16)

| Agent | 版本 | 行数 | 说明 |
|-------|:--:|:--:|------|
| **coordinator** | v3.1 | 630 | DAG 调度 + 规则引擎 + 4-Worker Queue |
| analyze-agent | v3 | 321 | 根因分析 + 双记忆 + 元认知 |
| fix-agent | v3 | 167 | 代码修复 + Self-Improvement Loop |
| review-agent | v3 | 207 | 3 轮审查 + 评分反馈 |
| decision-engine | v2 | 108 | 多模型 5 轮辩论 |
| test-agent | v3 | 426 | 3-Phase Evidence Pipeline |
| deploy-agent | v2 | 144 | Git MR + Jira 更新 |
| jira-agent | v4 | 345 | Jira 创建 + 8 段回填 |
| sls-agent | v3 | 96 | SLS 全量拉取 |
| db-agent | v2 | 72 | DMS 数据库验证 |
| io-agent | v2 | 74 | Git 仓库操作 |
| cost-tracker | v2 | 103 | Token/API 成本 |
| skill-executor | v1 | 355 | DAG 执行引擎 |
| workflow-driver | v1 | 372 | AI-Native TDD |
| sls-log-analysis | v1 | 153 | 全级别日志梳理 |
| production-incident-fix | v2 | 135 | 生产故障排查 |

### 开发流水线 (6)

| Agent | 版本 | 说明 |
|-------|:--:|------|
| **dev-harness** | v1 | 12 层全栈开发 DAG 调度器 |
| architecture-analyzer | v1 | 服务拓扑分析 (DB/Redis/MQ/Kafka) |
| requirement-analyzer | v1 | PRD 解析 + 服务匹配 |
| frontend-tracer | v1 | UI→API 调用链追踪 |
| code-designer | v1 | 架构感知方案设计 |

### Continuous Loop (9)

| Agent | 说明 |
|-------|------|
| **continuous-loop** | 8 阶段闭环调度器 |
| ① **ai-chat** | 需求采集对话 |
| ② **brewer** | PRD 生成 |
| ③ **distiller** | 技术规格提取 |
| ④ **taster** | 测试计划 (TDD) |
| ⑤ **gitlab-dev** | 开发实现 |
| ⑥ **crossfire** | 3 轮交叉验证 |
| ⑦ **destroyer** | 缺陷根因分析 |
| ⑧ **nebula** | 知识沉淀 (↻ 反哺) |

### 综合 DAG (1)

| Agent | 说明 |
|-------|------|
| **prd-to-verified-coordinator** | PRD→验证通过 13 层 DAG (24 步, Stargate 架构) |

---

## 三大核心原则 (v3.1)

### 1. 迭代优于单次
```
fix → review → score < 7 → fix(revision) → max 3 rounds
```

### 2. 记忆优于状态
```
Dual Memory: Pattern Match (index.md) + Similarity Search (历史案例)
```

### 3. 自知优于盲动
```
AUTO_FIX (conf ≥ 0.85) / NEEDS_HUMAN (0.60-0.74) / ESCALATE (< 0.60)
```

---

## Continuous Loop 循环

```
① AI Chat ──→ ② Brewer ──→ ③ Distiller ──→ ④ Taster
  需求采集       PRD 生成      技术规格提取    测试先行(TDD)
                                                  ↓
⑧ Nebula ←── ⑦ Destroyer ←── ⑥ Crossfire ←── ⑤ GitLab
  知识沉淀      根因分析        交叉验证(3轮)    开发实现
   ↓
  反哺 ① (下一次循环更聪明)
```

## PRD → Verified DAG (24 步, 13 层)

```
████████████░░░░░░░░░░░░░░  62%  (Layer 7/13)

✅ L0  AI Chat           [DONE]    需求采集
✅ L1  Brewer            [DONE]    PRD 生成
✅ L2  Distiller/Arch/KB [DONE]    技术提取+架构分析+知识库 (并行×3)
✅ L3  FE/BE Trace       [DONE]    前后端追踪 (并行×2)
✅ L4  Code Designer     [DONE]    方案设计
✅ L5  Design Review     [DONE]    方案评审 (score: 8.5)
✅ L6  Taster            [DONE]    测试计划
🔄 L7  Data/API/Biz      [RUNNING] 三层代码 (并行×3)
⏳ L8  Lint/Type/Test    [PENDING] 质量门禁
⏳ L9  Crossfire R1-R3   [PENDING] 交叉验证 (并行×3)
⏳ L10 Quality Gate      [PENDING] 质量关 (score≥7?)
⏳ L11 Git MR + Jira     [PENDING] 交付
⏳ L12 Nebula + Verify   [PENDING] 沉淀+验证
```

### DAG 引擎 (skill-executor)
- 拓扑排序 → 分层并行 → 引用解析 (`${steps.X.output.Y}`)
- Gate 自动回退 (`on_fail: return_to_step`)
- 状态持久化 (`skills/state/`), 进度实时追踪

---

## 知识库

| 维度 | 数量 |
|------|:--:|
| L1 简单模式 | 8 |
| L2 中等模式 | 5 |
| L3 复杂模式 | 3 |
| 不可修复模式 | 3 |
| SOP | 3 |
| 服务文档 | 2 |

### RAG 向量检索
- ChromaDB · all-MiniLM-L6-v2 · Markdown 分块 · Top-K=5

---

## 相互学习

```
opencode/        claude/
  agents/ ←─→    agents/      diff -rq → rsync 手动同步
  skills/ ←─→    skills/
  knowledge/ ←─→ knowledge/
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|:--:|------|------|
| v3.2 | 2026-05-28 | PRD-to-Verified DAG (24 步, 13 层, Stargate 架构) |
| v3.1 | 2026-05-28 | Continuous Loop 8 阶段 + 9 新 Agent |
| v3.0 | 2026-05-18 | DAG Scheduler + 4-Worker Queue + Skill Executor |
| v2.0 | 2026-04 | Decision Engine v2 (多模型 5 轮) |
| v1.0 | 2026-03 | 初始系统 (分析+修复+审查+部署) |

## 参考

- [all-agentic-architectures](https://github.com/FareedKhan-dev/all-agentic-architectures) — 17 种 Agent 架构
- [Stargate](https://stargate.lf.emmc.cc) — SkillOrchestrator DAG 引擎
- [OpenCode](https://opencode.ai) — Agent/Skill 规范
