# OpenCode Agent System

基于 [OpenCode](https://opencode.ai) 的生产级多 Agent 协作平台。两套**独立副本**（`opencode/` 和 `claude/`）各自演化、相互学习，用于自动化生产故障排查修复与全流程开发。

---

## 目录结构

```
├── opencode/                          ← ~/.config/opencode/ 独立副本
│   ├── agents/   (16 agents, 3708 行)
│   ├── skills/   (25 skills, 22 个子目录)
│   ├── knowledge/ (19 条知识模式 + 3 SOP + 2 服务文档)
│   ├── rag/       (ChromaDB 向量检索)
│   ├── opencode.json
│   ├── known-services.yaml (257 行, 服务注册表)
│   ├── decision-rules.yaml (241 行, 决策引擎规则)
│   ├── fix-patterns.md      (112 行, 修复模式索引)
│   └── session-cache.yaml
│
├── claude/                             ← ~/.claude/ 独立副本
│   ├── agents/   (16 agents, 同 opencode)
│   ├── skills/   (25 skills, 同 opencode)
│   ├── knowledge/ (同 opencode)
│   ├── CLAUDE.md (Claude CLI 协调器)
│   └── settings.json
│
├── agentic-architectures-analysis.md   ← 17 种架构学习分析报告
└── README.md
```

> **两套独立副本**。opencode 和 claude 各有自己的 agents/skills/knowledge，各自演化、手动相互学习。

---

## 架构总览

```
                    ┌─────────────────────────┐
                    │       User (输入)        │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  PRIMARY AGENT (自动选择) │
                    │  production-incident-fix │
                    │  sls-log-analysis         │
                    │  coordinator (DAG 调度)   │
                    └───────────┬─────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
   ┌──────────┐         ┌────────────┐         ┌─────────────┐
   │ Skill    │         │ Subagent   │         │ Coordinator │
   │ 触发执行  │         │ 通过Task调用 │         │ DAG 编排    │
   └──────────┘         └────────────┘         └─────────────┘
```

### 生产故障修复 DAG

```
Layer 0:    [Git Prep] ──────────── [SLS Scan]              并行
Layer 1:    [Jira Create] ───────── [DB Check]              并行(db条件)
Layer 2:    [Analyze Root Cause]    ← 双记忆检索 + 元认知评估
Layer 3:    [Code Fix]              ← Self-Improvement Loop  ─────────┐
Layer 4:    [R1 Compile] [R2 Thread] [Test]                 并行      │
Layer 5:    [R3 Production] + [Quality Gate]                          │
Layer 5a:   [score < 7? → 反馈 fix-agent 重新修复, max 3 轮] ───────┘
Layer 6:    [Deploy + MR]
Layer 7:    [Report Backfill]
Layer 8:    [Verify]
Each Step: [Cost Tracker]
```

---

## Agents 详细清单

### Primary Agents (自动触发)

| Agent | 版本 | 行数 | 模型 | 功能 |
|-------|:----:|:----:|------|------|
| **coordinator** | v3.1 | 630 | Claude Sonnet 4.6 | DAG 调度引擎 + 强制规则引擎 + 4-Worker 并行队列 + Skill Executor 集成 + SLA 监控 |
| **production-incident-fix** | v2 | 135 | Claude Sonnet 4.6 | 生产故障全流程修复：SLS → 分析 → 修复 → 测试 → Jira → MR |
| **sls-log-analysis** | v1 | 153 | Claude Sonnet 4.6 | 全级别 SLS 日志梳理：INFO/WARN/ERROR 三级 + 5-Agent 协作分类 + 健康报告 |

### Subagents (通过 Task 工具调用)

#### 分析与修复层

| Agent | 版本 | 行数 | 模型 | 核心能力 |
|-------|:----:|:----:|------|----------|
| **analyze-agent** | v3 | 321 | Claude Sonnet 4.6 | 根因分析 + **双记忆系统**（模式匹配 + 相似度搜索）+ **元认知评估**（AUTO_FIX / NEEDS_HUMAN / ESCALATE）+ 知识自动沉淀 |
| **fix-agent** | v3 | 167 | Claude Sonnet 4.6 | 代码修复 + **Self-Improvement Loop**（接收 review 反馈重新修复，max 3 轮）+ 修订历史追踪 |
| **decision-engine** | v2 | 108 | Claude Sonnet 4.6 | **多模型 5 轮辩论**（按问题级别动态轮次：L1=3轮 / L2=4轮 / L3=5轮）+ 6 模型路由 |

#### 审查与测试层

| Agent | 版本 | 行数 | 模型 | 核心能力 |
|-------|:----:|:----:|------|----------|
| **review-agent** | v3 | 207 | Claude Sonnet 4.6 | **三轮审查 + 评分反馈循环**：R1(编译) → R2(线程安全) → R3(生产就绪) → 综合评分 → score < 7 触发修订 |
| **test-agent** | v3 | 426 | Claude Sonnet 4.6 | 3-Phase Evidence Pipeline：L0 Index → L1 Capsules → L2 Evidence → Generate → Validate |

#### 工程工具层

| Agent | 版本 | 行数 | 模型 | 核心能力 |
|-------|:----:|:----:|------|----------|
| **deploy-agent** | v2 | 144 | Claude Sonnet 4.6 | Git commit + push + GitLab MR 自动创建 + Jira 更新 + 回滚验证 |
| **jira-agent** | v4 | 345 | Claude Sonnet 4.6 | Jira 创建（完整模板 + plan.md 附件）+ 回填（8 段 MD 报告 + worklog + comment） |
| **sls-agent** | v3 | 96 | Claude Sonnet 4.6 | SLS GetHistograms + GetLogsV2 分页全量拉取，无行数限制 |
| **db-agent** | v2 | 72 | Claude Sonnet 4.6 | DMS 数据库 Schema 查询 + 表结构验证（条件触发：仅在 SQL 错误时执行） |
| **io-agent** | v2 | 74 | Claude Sonnet 4.6 | Git 仓库克隆 + 分支创建 + 文件 I/O 进度追踪 |
| **cost-tracker** | v2 | 103 | Claude Sonnet 4.6 | 每步 token/API/cost 记录 → cost-log.jsonl + 成本异常告警 |
| **skill-executor** | v1 | 355 | Claude Sonnet 4.6 | Skill DAG 执行引擎：解析 DSL JSON → 拓扑排序 → 分层并行执行 |
| **workflow-driver** | v1 | 372 | DeepSeek V4 Pro Max | AI-Native TDD 循环：Spec → Generate Tests → Generate Impl → 5 Eval Gates → Ship |

---

## Skills 详细清单 (25 个)

### 生产运维 (Production Ops)

| Skill | 触发条件 | 说明 |
|-------|----------|------|
| **production-incident-fix** | `生产报错` `SLS日志分析` `代码修复` `P4` `hotfix` | 生产故障全流程：SLS 拉取 → 错误分析 → 代码修复 → 单元测试 → Jira → MR |
| **sls-log-analysis** | `日志梳理` `log analysis` `全级别扫描` `SLS分析` | 全级别日志梳理：INFO/WARN/ERROR 三级，5-Agent 协作分类，生成健康报告并上传 Jira |
| **code-review** | `提交` `commit` `push` `MR` `merge` `评审` `review` | 三轮对抗式 AI 代码审查：R1(Claude) → R2(Gemini) → R3(GPT)，三模型交叉验证 |
| **quality-control** | 代码生成完成 | 强制验证：linting → 测试 → 代码审查，报告完成前必须通过 |

### 数据库

| Skill | 触发条件 | 说明 |
|-------|----------|------|
| **dms-sql** | 用户粘贴 SQL 语句(SELECT/SHOW/EXPLAIN) | DMS Enterprise 跑 SQL，自动 schema → DbId 解析，结果 markdown 表格 |
| **dms-sql-cmd** | `/dms-sql <SQL...>` | 同上，命令行方式触发 |
| **sql-review-skill** | SQL 审查需求 | SQL 安全与性能审查：风险清单 + 改写建议 + 上线验证步骤 |

### 开发流程

| Skill | 触发条件 | 说明 |
|-------|----------|------|
| **dev-prep** | 需求文档 + P4 编号 | 预先准备：创建任务 → 关联 P4 → feature 分支 → 开发计划 |
| **dev-workflow** | `start a task` `new branch` `implement X` | cube-new 端到端开发循环：分支 → 实现 → gate → MR → deploy |
| **ai-native-tdd** | 实现功能、编写代码、开发需求 | TDD 强制：测试先行，测试是代码的合约 |
| **specs-as-code** | 需求文档、PRD、功能描述 | Left-Shift LS-02：PRD → 可执行 schema/eval/acceptance |
| **standard-dev-prep** | 创建 Jira/PR、分支、计划 | 标准需求开发前期准备 |
| **standard-requirement-dev-prep** | 开始新需求实现 | 自动化前期准备：创建任务 + 分支 + 计划 + 预估更新 |

### 代码质量

| Skill | 触发条件 | 说明 |
|-------|----------|------|
| **auto-eval** | 代码生成后 | 自动评估门禁：lint(20) + typecheck(20) + test(25) + coverage(15) + security(10) + complexity(10)，总分 100 |
| **auto-ship** | auto-eval 通过(≥80) | 自动交付：创建 MR → 监控 CI → 合并/退回 |
| **code-assistant-strict** | 重构、架构变更、复杂功能 | 严格代码助手：强制验证 → 测试 → linting → 结构化执行 |

### 评审流程

| Skill | 触发条件 | 说明 |
|-------|----------|------|
| **intake-review** | `triage issue` `intake review` `evaluate issue` | 入口门禁：Issue 评估 → 红牌规则 → 5 维度评分 → intake::* 标签 |
| **pr-eval** | `evaluate MR` `pr eval` `is this mergeable` | 出口门禁：MR diff 评估 → 范围漂移检测 → 5 维度评分 → pr-eval::* 标签 |
| **vcodes-pr** | `review PR` `submit PR` `create MR` | 两阶段 PR/MR：Phase 1 代码审查 + Phase 2 质量门禁，输出 PR-REPORT.md |
| **vcodes-qa** | `QA` `test this` `find bugs` | QA 测试：Playwright E2E + 手动验证，结构化 Bug Report |
| **vcodes-write-codes** | `write code` `implement` `build` | 全栈编码标准：DRY + 组件复用 + 共享 API Client + 类型安全 + 测试覆盖 |

### 前端专用

| Skill | 触发条件 | 说明 |
|-------|----------|------|
| **frontend-coding-skill** | 前端编码 | React/TypeScript 规范：样式、API 与工程约束 |
| **frontend-dev-workflow-skill** | 前端开发 | 前端开发工作流：分支、提交流程与质量门禁 |
| **frontend-mr-review-skill** | 前端 MR 评审 | 前端 MR 评审与提交：质量门禁、测试与提交流程 |
| **frontend-qa-skill** | 前端测试 | 前端 QA 规范：Vitest + Playwright |

---

## 知识库 (Knowledge Base)

### 规模统计

| 维度 | 数量 |
|------|:----:|
| 总条目 | 19 |
| 活跃条目 | 19 |
| 过时/归档 | 0 |
| L1 简单模式 | 8 条 |
| L2 中等模式 | 5 条 |
| L3 复杂模式 | 3 条 |
| 不可修复模式 | 3 条 (U001-U005) |
| 标准处理流程 (SOP) | 3 条 |
| 服务架构文档 | 2 个服务 |
| 知识管理规则 | 124 行 YAML |

### 知识库索引

#### L1 简单模式 (3 轮裁决)

| ID | 模式 | 匹配特征 |
|----|------|----------|
| K001 | Jackson 未知字段 | `Unrecognized field.*not marked as ignorable` |
| K002 | Logger null message | `log.error.*e.getMessage()` |
| K003 | e.printStackTrace | catch 块 `e.printStackTrace()` |
| K004 | error 降 warn | 正常业务态报 ERROR |
| K005 | 空值 null 检查 | NPE 无防御 |
| K012 | Secret 硬编码 | 配置文件含密码/Token 明文 |
| N001 | ES document_missing | `document_missing_exception` + update retry |

#### L2 中等模式 (4 轮裁决)

| ID | 模式 | 匹配特征 |
|----|------|----------|
| K006 | Feign null guard | `FeignException` + null 参数 |
| K007 | 响应 null 检查 | `restTemplate.postForObject` 无 null 判断 |
| K008 | serviceCycleCount 空 | fallback 仍 null |
| K010 | MCP 连接断开 | MCP tool call timeout/connection error |
| K011 | 技能重复执行 | 相同技能并发跑 |

#### L3 复杂模式 (5 轮裁决)

| ID | 模式 | 匹配特征 |
|----|------|----------|
| K009 | parallelStream NPE | ForkJoinTask `NullPointerException` |
| K013 | Redis 锁泄漏 | `Unable to connect.*Redis` + finally 缺失 |
| K014 | 序列化不一致 | `SerializationException` + Redis valueSerializer |

#### 不可修复模式

| ID | 标签 | 说明 |
|----|------|------|
| U001 | UPSTREAM | BBC 回调返回操作失败 |
| U002 | UPSTREAM | Feign 404, 下游端点不存在 |
| U003 | CONFIG | @DS 注解指向错误数据库 |
| U004 | DEPENDENCY | billing-middleware 版本不一致 |
| U005 | DATA | Authing 无效用户 ID |

### 标准处理流程 (SOP)

| SOP | 触发条件 |
|-----|----------|
| SOP-000 | 被动发现快速处理 |
| SOP-001 | @Transactional + @DS 多数据源冲突 |
| SOP-002 | K8s RollingUpdate Redis 连接池耗尽 |

### 服务知识库

| 服务 | 已知陷阱 |
|------|----------|
| contract-service | @Transactional+@DS 冲突 / Redis 连接池泄漏 / Zombie RedisMessageListenerContainer |
| stargate | MCP 连接池模式 / 技能系统 DSL / 3 轮对抗审查 / Fernet 加密 |

---

## 三大核心原则 (v3.1)

### 1. 迭代优于单次 — Self-Improvement Loop

```
fix → review(R1→R2→R3) → overall_score < 7? → fix(revision, with feedback)
                                                       ↓
                                                 review → score < 7? → fix(revision, round 2)
                                                                           ↓
                                                                     review → DONE 或 REVISION_EXHAUSTED
```

- `@inspire`: [all-agentic-architectures/15_RLHF.ipynb](https://github.com/FareedKhan-dev/all-agentic-architectures)
- `quality_threshold`: 7/10
- `max_revision_rounds`: 3
- `revision_strategy`: targeted (只改 review 指出的问题)

### 2. 记忆优于无状态 — Dual Memory

```
分析前:
  Step 0a: Pattern Match   → knowledge/index.md (精确正则匹配)
  Step 0b: Similarity Search → 历史案例检索 (关键词 + 结构相似度)
  Step 0c: Service Knowledge  → knowledge/services/ (已知陷阱)

成功后:
  Step 5: Knowledge Deposition → 自动沉淀新案例到知识库
```

- `@inspire`: [all-agentic-architectures/08_episodic_with_semantic.ipynb](https://github.com/FareedKhan-dev/all-agentic-architectures)
- Semantic Memory (规则匹配) + Episodic Memory (历史案例) + RAG (ChromaDB 向量检索)

### 3. 自知优于盲动 — Metacognitive

```
Agent Self-Model:
  knowledge_domains: [Java, Spring, Redis, Feign, MyBatis, 并发]
  limitations: [业务逻辑变更, 架构级问题, SDK bug, Schema 迁移]

置信度评估:
  confidence >= 0.85 → AUTO_FIX (自动修复)
  0.60 <= conf < 0.85 → NEEDS_HUMAN (标记人工审核, 仍执行修复)
  confidence < 0.60 → ESCALATE (不执行修复, 仅记录原因)
```

- `@inspire`: [all-agentic-architectures/17_reflexive_metacognitive.ipynb](https://github.com/FareedKhan-dev/all-agentic-architectures)

---

## 技术架构

### 多模型路由 (Decision Engine)

| 阶段 | 主模型 | 副模型 |
|------|--------|--------|
| 错误分类 | Claude Sonnet 4.6 | GPT-5.3 Codex |
| 根因分析 | GPT-5.3 Codex | Claude Sonnet 4.6 |
| 代码修复 | Claude Sonnet 4.6 | GPT-5.3 Codex |
| R1 编译审查 | GPT-5.3 Codex | DeepSeek V4 Pro Max |
| R2 线程安全 | Kimi K2.6 | Claude Sonnet 4.6 |
| R3 生产就绪 | DeepSeek V4 Pro Max | Claude Sonnet 4.6 |

### 辩论轮次 (按问题级别)

| 级别 | 轮次 | 适用场景 |
|:----:|:----:|----------|
| L1 | 3 轮 | 日志级别/null检查/注解 |
| L2 | 4 轮 | 异常处理/防御编码/序列化 |
| L3 | 5 轮 | 线程安全/锁逻辑/业务变更 |

### RAG 向量检索

```yaml
向量引擎: ChromaDB (persist)
嵌入模型: all-MiniLM-L6-v2 (fallback: paraphrase-multilingual-MiniLM-L12-v2)
分块策略: markdown_header (chunk_size=1000, overlap=200)
知识源: ~/.config/opencode/knowledge/**/*.md
默认 Top-K: 5
相似度阈值: 0.5
```

### 集成工具

| 工具类别 | 工具来源 | 说明 |
|----------|----------|------|
| 日志系统 | SLS (阿里云) | GetHistograms + GetLogsV2，全量分页拉取 |
| 项目管理 | Jira (Server/DC) | 创建/更新/评论/附件/状态流转/工时 |
| 代码仓库 | GitLab | MR 创建/审查/合并/分支管理/代码搜索 |
| 数据库 | DMS Enterprise | Schema 查询/表结构/字段搜索/影响分析 |
| 数据库 | Platform DB | DDL 解析/Schema 管理/关系图谱/同步到 KG |
| 知识图谱 | Stargate KG (Nebula/Neo4j) | 概念搜索/影响分析/代码定位/语境查询 |
| 云资产 | Eagle Eye | 资产总览/指标监控/成本分析/K8s 状态/Kafka Lag |
| 企业协作 | Feishu | 文档读写/图表渲染/Bitable 查询/Wiki 操作 |

---

## 治理与安全

### 质量门禁

```
Husky pre-commit → lint-staged (ESLint)
Husky pre-push   → typecheck + related tests
pr:check         → lint + typecheck + test + jscpd + build + feature-e2e
CI               → mirrors pr:check (本地通过 = CI 通过)
```

### MR 约束 (不可变更)

| 参数 | 固定值 | 说明 |
|------|:------:|------|
| target_branch | master | 禁止合到 develop |
| remove_source | false | 合并后保留源分支 |
| squash | false | 不压缩提交 |
| auto_merge | **false** | 禁止自动合并 |
| auto_create | **true** | 必须自动创建 MR |
| title | `[AI AutoFix] {service} — {summary}` | 标题前缀 |

### 预算控制

| 参数 | 默认值 | 说明 |
|------|:------:|------|
| budget_usd | $3.00 | 单次执行总预算 |
| budget_chunks | 100K tokens | 单步聊天块预算 |
| timeout_seconds | 600 | 单步最大执行时长 |
| max_concurrent | 4 | 同层并行步数上限 |

---

## 相互学习流程

```
~/.config/opencode/          ~/.claude/
    ├── agents/  ◄── 手动同步 ──►  ├── agents/
    ├── skills/  ◄── 手动同步 ──►  ├── skills/
    └── knowledge/ ◄─ 手动同步 ──► └── knowledge/
```

```bash
# 查看差异
diff -rq opencode/agents/ claude/agents/
diff -rq opencode/skills/ claude/skills/

# 同步方向 (任选)
rsync -av opencode/agents/ claude/agents/     # opencode → claude
rsync -av claude/agents/ opencode/agents/     # claude → opencode
```

---

## 灵感来源

- [all-agentic-architectures](https://github.com/FareedKhan-dev/all-agentic-architectures) — 17 种现代 Agent 架构教学实现
  - Self-Improvement Loop (RLHF)
  - Episodic + Semantic Memory
  - Reflexive Metacognitive
  - Blackboard Systems
  - PEV (Plan-Execute-Verify)
  - Tree of Thoughts
- [OpenCode](https://opencode.ai) — Agent/Skill 定义规范
- [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) — Agent 角色定义规范

---

## 版本历史

| 版本 | 日期 | 变更 |
|:----:|------|------|
| v3.1 | 2026-05-28 | Self-Improvement Loop + Dual Memory + Metacognitive v3 |
| v3.0 | 2026-05-18 | DAG Scheduler + 4-Worker Queue + Skill Executor |
| v2.0 | 2026-04 | Decision Engine v2 (多模型路由 + 5 轮辩论) |
| v1.0 | 2026-03 | 初始 Agent 系统：analyze + fix + review + deploy |
