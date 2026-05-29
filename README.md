# OpenCode Multi-Agent System

[![Agents](https://img.shields.io/badge/Agents-44-blue)](./opencode/agents/)
[![Skills](https://img.shields.io/badge/Skills-32-green)](./opencode/skills/)
[![Patterns](https://img.shields.io/badge/Patterns-20/21-orange)](./agentic-architectures-analysis.md)
[![Status](https://img.shields.io/badge/Status-Production-brightgreen)]()

基于 [OpenCode](https://opencode.ai) 的生产级多 Agent 协作平台，**44 个 Agent + 32 个 Skill + 5 套 DAG 流水线**，覆盖 21 种 AI Agent 架构中 **20/21 种**。

**v3.7 代码审查增强版**：三轮对抗式审查 DAG + CI 编译门禁 + 链式 API 盲区预防。

---

## 四流水线架构

```
┌─────────────────────────────────────────────────────────────┐
│                     OpenCode Agent System                     │
│                       44 Agents · 20/21 模式                  │
├─────────────────┬─────────────────┬─────────────────────────┤
│  修复流水线       │  开发流水线       │  Continuous Loop        │
│  (coordinator)   │  (dev-harness)   │  (continuous-loop)      │
│  生产故障排查      │  全栈 Harness DAG │  8 阶段闭环开发          │
│  → Bug Fix       │  → Feature Dev   │  → PRD → Verify ↻       │
├─────────────────┼─────────────────┼─────────────────────────┤
│  审查流水线 (v3.7 新增)                                  │
│  (code-review-dag)                                       │
│  R1 审查 → R2 挑战 → R3 裁定 + CI 编译门禁                  │
├─────────────────┼─────────────────┼─────────────────────────┤
│  Hermes 增强层                                          │
│  ├─ security-gate      安全审批门                         │
│  ├─ context-compressor 上下文压缩                         │
│  ├─ delegation         并行委托                           │
│  └─ mental-simulator   内心模拟/干运行                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
├── opencode/                          ← ~/.config/opencode/
│   ├── agents/      44 agents (v3.7)
│   ├── skills/      32 skills · 5 DAG
│   ├── knowledge/   19 模式 + 3 SOP + 2 服务文档
│   ├── rag/         ChromaDB 向量检索
│   └── opencode.json
│
├── claude/                             ← ~/.claude/ 独立副本
│   ├── agents/     39 agents (v3.3 同步)
│   ├── skills/     32 skills
│   ├── knowledge/  同 opencode
│   └── CLAUDE.md
│
├── agentic-architectures-analysis.md   ← 21 种架构学习报告
└── service-knowledge/                  ← 服务知识库
```

---

## Agent 清单 (44)

### 修复流水线 (16)

| Agent | 版本 | 说明 |
|-------|:--:|------|
| **coordinator** | v3.1 | DAG 调度 + 规则引擎 + 4-Worker Queue |
| analyze-agent | v3 | 根因分析 + 双记忆 + 元认知 |
| fix-agent | **v4** ↑ | 代码修复 + 安全扫描 + 内心模拟 |
| review-agent | **v4** ↑ | 3 轮审查 + 大文件上下文压缩 |
| decision-engine | v2 | 多模型 5 轮辩论 |
| test-agent | v3 | 3-Phase Evidence Pipeline |
| deploy-agent | **v3** ↑ | Git MR + 干运行 + 安全门 |
| jira-agent | v4 | Jira 创建 + 8 段回填 |
| sls-agent | v3 | SLS 全量拉取 |
| db-agent | v2 | DMS 数据库验证 |
| io-agent | v2 | Git 仓库操作 |
| cost-tracker | v2 | Token/API 成本 |
| skill-executor | v1 | DAG 执行引擎 |
| workflow-driver | v1 | AI-Native TDD |
| sls-log-analysis | v1 | 全级别日志梳理 |
| production-incident-fix | v2 | 生产故障排查 |

### 开发流水线 (7, +2 新)

| Agent | 版本 | 说明 |
|-------|:--:|------|
| **dev-harness** | v1 | 12 层全栈开发 DAG 调度器 |
| architecture-analyzer | v1 | 服务拓扑分析 |
| requirement-analyzer | v1 | PRD 解析 + 服务匹配 |
| frontend-tracer | v1 | UI→API 调用链追踪 |
| code-designer | v1 | 架构感知方案设计 |
| **security-gate-agent** | **v1 new** | 安全审批门 + 威胁扫描 |
| **mental-simulator-agent** | **v1 new** | 内心模拟 + 干运行 |

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

### 审查流水线 (5, v3.7 新增)

| Agent | 版本 | 说明 |
|-------|:--:|------|
| **code-review-dag** | **v2.0** | 三轮对抗式审查 DAG 调度器 + CI 编译门禁 |
| **r1-reviewer** | **v2.0** | 逐行审查 + 链式 API 盲区检测 |
| **r2-challenger** | v1.0 | 逐条质疑 R1 + 补充遗漏 |
| **r3-arbiter** | v1.0 | 综合裁定 + 评分 + 合并建议 (Kimi K2.6) |
| **report-saver** | v1.0 | 审查/测试报告 Markdown 生成 |

### 基础能力层 (7, +2 新)

| Agent | 版本 | 说明 |
|-------|:--:|------|
| memory-agent | **v1.1** ↑ | 双记忆 (引用 SQLite+FTS5) |
| meta-cognitive-agent | **v1.1** ↑ | 元认知安全 (引用 security.py) |
| self-improve-agent | **v1.1** ↑ | Self-Improvement (引用 skills.py) |
| service-cataloger | v1 | 服务知识图谱 |
| **delegation-agent** | **v1 new** | 并行子代理委托 |
| **context-compressor-agent** | **v1 new** | Token 预算管理 |
| prd-to-verified-coordinator | v1 | 13 层 PRD→Verified DAG |

---

## 架构模式覆盖：19/21

| 已覆盖 (19) | Hermes 增强 | 待补充 (2) |
|------------|------------|-----------|
| Reflection, Tool Use, ReAct | ✅ 已实现 | Tree of Thoughts |
| Planning, Multi-Agent, PEV | ✅ 已实现 | Cellular Automata |
| Blackboard, Episodic+Semantic | ✅ 已实现 | |
| **Context Compression** | **v3.3 新增** | |
| Mental Loop, Meta-Controller | ✅ 已实现 | |
| Graph Memory, Ensemble | ✅ 已实现 | |
| **Dry-Run** | **v3.3 新增** | |
| RLHF/Self-Improvement | ✅ 已实现 | |
| Metacognitive | ✅ 已实现 | |
| **Plugin System** | **v3.3 新增** | |
| **Delegation** | **v3.3 新增** | |
| **Security Gate** | **v3.3 新增** | |

---

## 三大核心原则

### 1. 三思后行 (v3.3 新增)
```
mental-simulator → security-gate → deploy
     内心模拟         安全审批        执行
```

### 2. 迭代优于单次
```
fix → review → score < 7 → fix(revision) → max 3 rounds
```

### 3. 自知优于盲动
```
AUTO_FIX (conf ≥ 0.85) / NEEDS_HUMAN (0.60-0.74) / ESCALATE (< 0.60)
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|:--:|------|------|
| **v3.7** | **2026-05-29** | **代码审查 DAG: 三轮对抗式审查 + CI 编译门禁 + 链式 API 盲区预防** |
| v3.6 | 2026-05-28 | 知识图谱(62节点112边) + 对话向量记忆 + 21服务文档扫描 |
| v3.5 | 2026-05-28 | RAG 云端 Supabase + 7 新 Agent + Pipeline DAG + Prompt Caching |
| v3.4 | 2026-05-28 | RAG 混合搜索 + Cron 定时 + Tree of Thoughts + Prompt Caching |
| v3.3 | 2026-05-28 | Hermes 增强: 压缩/委托/模拟 + 3 新 Agent + 6 升级 |
| v3.2 | 2026-05-28 | PRD-to-Verified DAG (24 步, 13 层, Stargate 架构) |
| v3.1 | 2026-05-28 | Continuous Loop 8 阶段 + 9 新 Agent |
| v3.0 | 2026-05-18 | DAG Scheduler + 4-Worker Queue + Skill Executor |
| v2.0 | 2026-04 | Decision Engine v2 (多模型 5 轮) |
| v1.0 | 2026-03 | 初始系统 (分析+修复+审查+部署) |

## 参考

- [ai-auto-study](https://github.com/Sxkl/ai-auto-study) — 21 种 Agent 架构学习引擎 + 生产共享库
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — 生产级 AI Agent (171k stars)
- [OpenCode](https://opencode.ai) — Agent/Skill 规范
