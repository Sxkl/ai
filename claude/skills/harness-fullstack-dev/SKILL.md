---
name: harness-fullstack-dev
description: Harness Engineering 全栈开发流水线。从 Jira PRD 出发：知识库扫描→架构分析→前后端追踪→方案设计→TDD编码→审查→Jira回填。多Agent并行协作+自审查循环。Use ONLY when developing fullstack features that require frontend+backend coordination. Trigger keywords: 全栈开发、前后端、Harness DAG、架构分析、方案设计、前端+后端、全流程开发
---

# Harness Engineering — 全栈开发自动化流水线

## 核心理念

从 Jira PRD 到代码审查的**全自动化开发流水线**。多 Agent 并行协作，Self-Review Loop 自动修正，人审结果不审过程。

```
Jira PRD → 知识库扫描 → 架构分析 → 前后端追踪 → 方案设计 → TDD → 编码 → 审查 → Jira回填
```

## DAG 流水线

12 层、22 步，由 `dev-harness` agent 调度：

| Layer | Step | Agent | 说明 | 并行 |
|:-----:|------|-------|------|:--:|
| 0 | prd_read | requirement-analyzer | 读取 Jira PRD, 解析需求 | ✅ |
| 0 | kb_scan | analyze-agent | 知识库扫描 (已知模式/服务/陷阱) | ✅ |
| 1 | arch | architecture-analyzer | 服务架构分析 (数据库/缓存/MQ/Kafka/依赖) | — |
| 2 | fe_trace | frontend-tracer | 前端 UI→API 调用链追踪 | ✅ |
| 2 | be_search | requirement-analyzer | 后端 Controller/Service 接口定位 | ✅ |
| 3 | design | code-designer | 方案设计 (复杂度评估+架构约束) | — |
| 3 | design_review | review-agent | 方案评审 (score ≥ 7 通过) | — |
| 4 | data_layer | workflow-driver | 数据层: Entity+Mapper+DDL | ✅ |
| 4 | api_layer | workflow-driver | 接口层: Controller+DTO+Feign | ✅ |
| 4 | biz_layer | workflow-driver | 业务层: Service+MQ+Cache | ✅ |
| 5 | gen_test | test-agent | TDD 测试生成 (测试先行) | — |
| 6 | gen_impl | workflow-driver | 实现代码生成 | — |
| 7 | lint | auto-eval | Lint 检查 | ✅ |
| 7 | typecheck | auto-eval | 类型检查 | ✅ |
| 7 | unit_test | test-agent | 单元测试执行 | ✅ |
| 8 | r1_review | review-agent | R1 代码审查 (正确性) | ✅ |
| 8 | r2_review | review-agent | R2 架构审查 (设计一致性) | ✅ |
| 9 | quality_gate | dev-harness | score < 7 → 回 Layer 6 (max 3) | — |
| 10 | git_mr | deploy-agent | Git commit + push + MR 创建 | — |
| 11 | jira_update | jira-agent | Jira 回填: description+worklog+comment | — |
| 12 | verify | dev-harness | 最终验证 | — |

## 核心 Agent 说明

### 新 Agent (5 个)

| Agent | 职责 |
|-------|------|
| `dev-harness` | 总调度器，12层DAG编排 + Self-Review Loop |
| `architecture-analyzer` | 分析服务拓扑：数据库/Redis/MQ/Kafka/Feign依赖 |
| `requirement-analyzer` | 解析 PRD → 匹配服务 → 定位模块 → 映射接口 |
| `frontend-tracer` | UI元素 → API调用 → 网关配置 完整追踪 |
| `code-designer` | 方案设计 + 复杂度评估 + 架构约束检查 |

### 复用现有 Agent (7 个)

| Agent | 复用角色 |
|-------|----------|
| `analyze-agent` | 知识库扫描 |
| `workflow-driver` | TDD代码生成 |
| `test-agent` | 测试生成+执行 |
| `review-agent` | 方案评审+代码审查 |
| `deploy-agent` | Git MR |
| `jira-agent` | Jira回填 |
| `auto-eval` | Lint+TypeCheck |

## 特殊能力

### 1. 架构感知编码
- 自动识别多数据源、Redis、MQ、Kafka
- 避免已知陷阱 (如 @Transactional+@DS 冲突、Redis锁泄漏)
- 复杂度评估 + 性能瓶颈识别
- 防御性编码规则自动注入

### 2. 前后端联动
- 前端: 搜索 UI 组件 → 追踪 API 调用 → 生成接口契约
- 后端: 搜索 Controller → 定位 Service → 设计实现方案
- 网关: 自动生成路由配置
- 类型一致性: snake_case 强制 + DTO 契约校验

### 3. Self-Review Loop
- 方案评审不通过 (score < 7) → 自动重新设计 (max 2)
- 代码审查不通过 (score < 7) → 自动重新实现 (max 3)
- 质量门禁不过 → 回炉重修

### 4. Jira 全生命周期
- 创建时: 自动建 PR 任务 + 关联 P4
- 设计完成: comment 设计方案摘要+复杂度
- 编码完成: comment 文件清单+测试通过率
- 完成时: transition + worklog + MR 链接

## 使用方式

输入 PR 编号即可触发:
```
PR-6312
```

或自然语言:
```
开发合同导出功能，前端在 ContractList 页面加导出按钮，后端 contract-service 新增导出接口
```

## 输出
- designs/: 方案设计文档
- test/: 测试用例
- src/: 实现代码
- MR: GitLab MR 链接
- Jira: 自动更新 status/worklog/description
