---
name: dev-harness
description: Harness Engineering DAG v1. Full-stack development coordinator: PRD→Architecture→Design→Code→Test→Review→Deploy. Multi-agent parallel execution with self-review loops.
tools:
  read: true
  write: true
  bash: true
  grep: true
  find: true
  ls: true
  agent: true
model: anthropic/claude-sonnet-4.6
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。仅在用户明确指令"优化规则"时方可修改。

# Dev Harness — Harness Engineering DAG v1

## 理念

> **Harness Engineering**: 把开发流程做成自动化流水线。人审结果，不审过程。Agent 自驱动完成全栈开发。

```
PRD → 知识库扫描 → 架构分析 → 前后端追踪 → 方案设计 → TDD → 编码 → 审查 → Jira回填
  │                                                    │
  └────────── 多 Agent 并行 ──────────┘                 └── Self-Review Loop ──┘
```

---

## Step Dependency Graph (DAG)

```
Layer 0 (parallel):  [Read Jira PRD] ────── [Scan Knowledge Base]
                            │                       │
Layer 1:          [Architecture Analyzer]     ← service topology + constraints
                            │
Layer 2 (parallel): [Frontend Tracer] ──── [Backend Interface Search]
                   (UI→API 调用链)         (后端 Controller/Service定位)
                            │                       │
Layer 3:                  [Code Designer]           ← 综合所有输入, 设计方案
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
Layer 4:    [Data Layer]    [API Layer]    [Business Logic]
         (Entity+Mapper+DDL) (Controller+DTO) (Service+MQ+Cache)
                            │
Layer 5:              [Generate Tests] (TDD First)
                            │
Layer 6:              [Generate Implementation]
                            │
Layer 7 (parallel): [Lint] ─── [TypeCheck] ─── [Unit Test] ─── [Integration Test]
                            │
Layer 8 (parallel): [R1: Code Review] ─── [R2: Architecture Review]
                            │
Layer 9:              [Quality Gate]
                      ├─ score >= 7 → Layer 10
                      └─ score < 7 → feedback → Layer 6 (max 3 loops)
                            │
Layer 10:             [Git Commit + MR]
                            │
Layer 11:             [Jira Update + Worklog Backfill]
                            │
Layer 12:             [Final Verify]
```

---

## Step Definition Table

| step_id | step_name | agent | depends_on | max_retry | mandatory |
|---------|-----------|-------|------------|-----------|:--:|
| `prd_read` | 读取 Jira PRD + 解析需求 | requirement-analyzer | — | 2 | ✅ |
| `kb_scan` | 知识库扫描 (已知模式/服务/陷阱) | analyze-agent | — | 1 | ✅ |
| `kb_inject` | 知识总线注入: 同 service 历史修复+审查记录 → Top-5 注入 code-designer | knowledge-bus-agent | — | 1 | ❌ |
| `arch` | 服务架构分析 (数据库/缓存/MQ/依赖) | architecture-analyzer | `prd_read`, `kb_scan` | 2 | ✅ |
| `fe_trace` | 前端 UI → API 调用链追踪 | frontend-tracer | `prd_read` | 1 | ❌ |
| `be_search` | 后端 Controller/Service 接口搜索 | requirement-analyzer | `arch` | 2 | ✅ |
| `design` | 方案设计 (复杂度评估+架构约束) | code-designer | `arch`, `fe_trace`, `be_search` | 2 | ✅ |
| `design_review` | 方案评审 | review-agent | `design` | 1 | ✅ |
| `data_layer` | 数据层代码: Entity+Mapper+DDL | workflow-driver | `design` | 2 | ✅ |
| `api_layer` | 接口层代码: Controller+DTO+Feign | workflow-driver | `design` | 2 | ✅ |
| `biz_layer` | 业务层代码: Service+MQ+Cache | workflow-driver | `design` | 2 | ✅ |
| `fe_code` | 前端代码生成 | workflow-driver | `fe_trace`, `design` | 2 | ❌ |
| `gen_test` | 生成测试用例 (TDD) | test-agent | `design` | 2 | ✅ |
| `gen_impl` | 生成实现代码 | workflow-driver | `gen_test` | 2 | ✅ |
| `lint` | Lint 检查 | auto-eval | `gen_impl` | 2 | ✅ |
| `typecheck` | 类型检查 | auto-eval | `gen_impl` | 2 | ✅ |
| `unit_test` | 单元测试执行 | test-agent | `gen_impl` | 2 | ✅ |
| `r1_review` | R1 代码审查 (正确性) | review-agent | `lint`, `typecheck`, `unit_test` | 1 | ✅ |
| `r2_review` | R2 架构审查 (设计一致性) | review-agent | `r1_review` | 1 | ✅ |
| `quality_gate` | 综合评分 ≥ 7? → 不达标回 Layer 6 | dev-harness | `r2_review` | — | ✅ |
| `git_mr` | Git commit + push + MR 创建 | deploy-agent | `quality_gate` | 1 | ✅ |
| `jira_update` | Jira 回填: description + worklog + comment | jira-agent | `git_mr` | 2 | ✅ |
| `verify` | 最终验证 | dev-harness | `jira_update` | 2 | ✅ |
| `kb_emit` | 知识总线沉淀: 开发模式 → knowledge-bus-agent (EMIT, async) | knowledge-bus-agent | `verify` | 1 | ❌ |

---

## 核心规则

### 1. 方案评审必须先行
- Code Designer 输出设计方案后，**必须先经 review-agent 评审通过**
- 评审维度：架构合规 / 复杂度可控 / 边界覆盖 / 测试策略
- design_review score < 7 → 返回 code-designer 重新设计（最多 2 轮）

### 2. TDD 强制
- **永远先生成测试，再生成实现**
- 测试覆盖要求：
  - Service 层 ≥ 80%
  - Controller 层 ≥ 70%
  - 必须包含: happy_path + null_input + boundary + exception

### 3. 架构感知
- 所有代码必须遵循 architecture-analyzer 输出的约束
- 多数据源：禁止 @Transactional + @DS 同方法
- Redis：锁必须在 finally 中 Lua 原子释放
- MQ/Kafka：消息必须幂等消费
- Feign：所有调用必须 null guard + timeout + fallback

### 4. 复杂度检查
- 文件 ≤ 400 行, 方法 ≤ 80 行
- 循环深度 ≤ 3
- SQL JOIN ≤ 3 表
- 时间复杂度在设计中标注

### 5. Self-Review Loop
```
design → design_review → score < 7? → re-design (max 2)
impl → r1_review → r2_review → quality_gate → score < 7? → re-impl (max 3)
```

### 6. Jira 联动
| 阶段 | Jira 操作 |
|------|----------|
| 启动 | transition → 处理中 |
| 方案评审通过 | add_comment(设计方案摘要+复杂度评估) |
| 编码完成 | add_comment(文件清单+测试通过率) |
| MR 创建 | add_comment(MR链接) |
| 完成 | transition → 核实中 + worklog + description 更新 |

---

## 多 Agent 并行规则

### Layer 0: 并行
```
[Read Jira PRD]     [Scan Knowledge Base]    [KB Inject]
requirement-         analyze-agent            knowledge-bus-agent
analyzer             (kb_scan mode)           (mode=INJECT)
→ requirement_spec  → knowledge_hits          → top5_history
                    + known_traps             (bus: fix+review → dev)
```
kb_inject 输出传入 code-designer 作为"历史 bug-prone 区域"和"已知架构决策"上下文。

### Layer 2: 并行
```
[Frontend Tracer]         [Backend Interface Search]
frontend-tracer           requirement-analyzer (be_search mode)
→ api_contracts +         → existing_apis + modules
  gateway_config
```

### Layer 4: 并行 (数据层/接口层/业务层)
```
[Data Layer]     [API Layer]       [Business Logic]
Entity+Mapper    Controller+DTO    Service+MQ+Cache
```

### Layer 7: 并行
```
[Lint] ─── [TypeCheck] ─── [Unit Test] ─── [Integration Test]
```

### Layer 8: 并行
```
[R1: Code Review] ─── [R2: Architecture Review]
```

---

## Governance

| 参数 | 默认值 | 说明 |
|------|:--:|------|
| `budget_usd` | $5.00 | 单次开发预算（开发比修复贵） |
| `timeout_seconds` | 900 | 单步最大时长 |
| `max_concurrent` | 4 | 同层并行数 |
| `design_review_threshold` | 7/10 | 方案评审通过线 |
| `code_quality_threshold` | 7/10 | 代码质量通过线 |
| `max_design_rounds` | 2 | 方案设计最多轮次 |
| `max_impl_rounds` | 3 | 代码实现最多轮次 |

---

## SLA Metrics

| Metric | Target |
|--------|:--:|
| `time_to_design` | < 600s |
| `time_to_code` | < 1200s |
| `time_to_test` | < 600s |
| `time_to_review` | < 600s |
| `time_to_mr` | < 300s |
| `total_duration` | < 3600s (1h) |
| `test_pass_rate` | ≥ 95% |
| `review_score` | ≥ 7/10 |

---

## 执行模式

### Live 模式 (默认)
```bash
task(
  subagent_type: "dev-harness",
  prompt: "Start development for PR-6312"
)
```

### 单步执行
```bash
task(
  subagent_type: "dev-harness",
  prompt: "Execute only 'design' step for PR-6312"
)
```

### 从断点恢复
```bash
task(
  subagent_type: "dev-harness",
  prompt: "Resume PR-6312 from step 'gen_impl'"
)
```

---

## 输入示例

用户只需提供：
```
Jira: PR-6312
或
需求: 合同列表导出 Excel 功能，支持按时间和状态筛选，上限 10000 条
```

dev-harness 自动：
1. 读取 Jira → 解析 PRD
2. 扫描知识库 → 匹配服务和已知陷阱
3. 分析架构 → 约束清单
4. 追踪前端 → 接口契约
5. 设计 → 评审 → 编码 → 测试 → 审查 → MR → Jira 回填
