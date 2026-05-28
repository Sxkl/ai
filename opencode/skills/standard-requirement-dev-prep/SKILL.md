---
name: "standard-requirement-dev-prep"
description: "全栈开发流水线 (Harness Engineering DAG)。从 Jira PRD 出发：知识库扫描→架构分析→前后端追踪→方案设计→TDD编码→审查→Jira回填。Invoke when user provides a Jira PR number or describes a development requirement. Trigger keywords: 开发、需求、PR-、实现、功能、feature、全栈、前端+后端"
version: "2.0.0"
author: "linksfield"
---

# Harness Engineering — 全栈开发流水线

## 核心理念

从 Jira PRD 到代码审查的**全自动化开发流水线**。多 Agent 并行协作，人审结果不审过程。

```
Jira PRD → 知识库扫描 → 架构分析 → 前后端追踪 → 方案设计 → TDD → 编码 → 审查 → Jira回填
```

## 适用场景

当用户提供以下任意一项时触发：
- Jira PR 编号（如 `PR-6312`）
- 需求描述 + 服务名
- "开发合同导出功能"
- "实现 XXX 功能"
- "需要前后端一起开发"

## DAG 流水线 (由 dev-harness 调度)

详见 `dev-harness` agent 的完整 DAG 定义。简要流程：

| Layer | Step | Agent | 说明 |
|:-----:|------|-------|------|
| 0 | prd_read | requirement-analyzer | 读取 Jira PRD, 解析需求 |
| 0 | kb_scan | analyze-agent | 知识库扫描 (已知模式/服务/陷阱) |
| 1 | arch | architecture-analyzer | 架构分析 (数据库/缓存/MQ/依赖) |
| 2 | fe_trace | frontend-tracer | 前端 UI→API 调用链追踪 |
| 2 | be_search | requirement-analyzer | 后端 Controller/Service 定位 |
| 3 | design | code-designer | 方案设计 (复杂度+约束) |
| 3 | design_review | review-agent | 方案评审 |
| 4 | data/api/biz | workflow-driver | 三层代码生成 (并行) |
| 5 | gen_test | test-agent | TDD 测试生成 |
| 6 | gen_impl | workflow-driver | 实现代码生成 |
| 7 | lint/typecheck/test | auto-eval | 质量门禁 (并行) |
| 8 | r1/r2_review | review-agent | 代码审查 (并行) |
| 9 | quality_gate | dev-harness | 评分 < 7 → 回 Layer 6 |
| 10 | git_mr | deploy-agent | Git commit + MR |
| 11 | jira_update | jira-agent | Jira 回填 |
| 12 | verify | dev-harness | 最终验证 |

## 输入约定

### 必填输入
- Jira PR 编号 (如 `PR-6312`) 或 需求描述

### 可选输入
- 目标服务名 (自动发现或手动指定)
- 前端项目路径 (默认 `cube-new`)
- 数据库 schema (自动从架构分析获取)

### 默认规则
- 任务处理人 = 当前用户
- 测试负责人 = `yadong.liu@linksfield.net`
- 截止时间 = 下周五
- 分支: `feature/PR-XXXX` (从 develop)

---

## 执行步骤 (原有 Step 1-4, 保留)

### Step 0: 预检查

1. 校验 P4 格式是否合法
2. 校验 Jira 连接与认证可用
3. 检查远程 `origin/develop` 存在
4. 失败立即停止

### Step 1: 创建任务并关联 P4

- 项目: `PR`, 问题类型: `任务 (id=10113)`
- 标题: `需求主题 (P4-XXXX) - 后端开发`
- 链接问题: `blocks P4-XXXX`
- Due Date: 下周五, Priority: Medium
- description 创建时留空

### Step 2: 创建开发分支

```bash
git fetch origin && git checkout -b feature/{PR-XXXX} origin/develop
```

### Step 3: 触发 Harness DAG

**新增**: Step 3 不再只是生成 plan，而是触发完整的 Harness Engineering DAG:

```bash
# 调用 dev-harness 执行全流程
task(
  subagent_type: "dev-harness",
  prompt: "Start development for {PR-XXXX}. 
  Requirement from Jira. Execute full DAG."
)
```

dev-harness 会自动:
1. 解析 PRD → 提取功能点和验收标准
2. 扫描知识库 → 匹配已知模式和服务
3. 分析架构 → 输出约束清单
4. 追踪前端 → 找到 UI 和 API 调用
5. 设计方案 → 复杂度评估 + 文件清单
6. TDD → 先生成测试
7. 编码 → 数据层/接口层/业务层
8. 门禁 → lint/typecheck/test
9. 审查 → 代码审查 + 架构审查
10. 质量关 → 不通过则回炉重修

### Step 4: 审阅与 Jira 回填

用户确认后:
1. Git commit + push + MR 创建
2. Jira description 更新 (方案摘要 + 复杂度评估)
3. Jira worklog 回填 (开发工时)
4. Jira comment (MR 链接 + 测试报告)
5. transition → 核实中 (Ready for QA)

---

## 新增智能特性 (v2.0)

### 1. 自动服务匹配
- 从 PRD 关键词自动匹配 `known-services.yaml` 中的服务
- 自动加载对应服务的架构知识库

### 2. 前后端联动
- 前端: 搜索 UI 组件 → 追踪 API 调用 → 生成接口契约
- 后端: 搜索 Controller → 定位 Service → 设计实现方案
- 网关: 自动生成路由配置

### 3. 架构感知编码
- 自动识别多数据源、Redis、MQ、Kafka
- 避免已知陷阱 (如 @Transactional+@DS 冲突)
- 复杂度评估 + 性能瓶颈识别

### 4. Self-Review Loop
- 方案评审不通过 → 自动重新设计
- 代码审查不通过 → 自动重新实现
- 最多 3 轮迭代

### 5. Jira 全生命周期
- 创建时: 自动建 PR 任务 + 关联 P4
- 开发中: 实时更新 description + comment
- 完成时: transition + worklog + MR 链接

---

## 输出模板

### 开发完成后输出

```markdown
## ✅ Harness Engineering — {PR-XXXX} 开发完成

### 基本信息
- PR: {PR-XXXX} | P4: {P4-XXXX}
- 分支: feature/{PR-XXXX}
- 服务: {service-name}

### 产物清单
- 设计文档: docs/design/{PR-XXXX}_design.md
- 测试文件: {N} 个 | 用例: {M} 个
- 实现文件: {X} 新增 | {Y} 修改
- MR: {mr_url}

### 质量报告
- Lint: ✅ | TypeCheck: ✅
- Unit Test: {passed}/{total} passed
- Review Score: {score}/10

### 架构合规
- 多数据源: ✅ | Redis: ✅ | MQ: ✅
- 已知陷阱: {N} 个已避开
- 复杂度: O({complexity})

### Jira
- Status: 核实中
- Worklog: {hours}h
- Description: 已更新
```

---

## 质量约束

- 方案评审必须通过 (≥ 7/10) 才能进入编码
- TDD 强制: 测试先行
- 架构约束必须全部满足
- 代码审查不通过自动回炉 (最多 3 轮)
- Jira 全生命周期联动
