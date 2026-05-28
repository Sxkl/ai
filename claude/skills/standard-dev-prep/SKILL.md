---
name: "standard-dev-prep"
description: "Runs pre-development preparation from requirement doc and P4. Invoke when user asks to create Jira/PR, branch, plan, and estimate updates before coding."
version: "1.0.0"
author: "linksfield"
---

# 标准需求开发前期准备 Skill

## 与 `dev-execution-plan-skill.md` 的关系

- 本模板定位为简版入口，详细与强约束流程以 `dev-execution-plan-skill.md` 为准
- 涉及 `Engineering 4.x (PR)` 项目时，必须继承完整版的强约束：
  - 先执行 Step 0 预检查并 fail-fast
  - Jira 创建显式使用 `issuetype.id=10113`
  - 禁止使用 P4 编号推断 PR 号
  - 提交前执行 snake_case 字段扫描

## 目标
在用户提供需求文档并给出 P4 编号后，标准化完成“开发前期准备”流程：
1. 建立并关联 Jira/PR；
2. 从远程 develop 拉分支；
3. 生成可审阅的初版开发计划；
4. 审阅通过后提交计划并回填工时与 worklog。

## 触发条件
- 用户提供需求文档（或需求链接/文本）；
- 用户给出 P4 编号；
- 用户希望开始开发前期准备、建分支、出 plan、回填工时。

## 输入要求
- `requirement_doc`：需求文档内容或链接
- `p4_key`：如 `P4-5340`
- `reporter`：报告人（若未给出，默认请求方）
- `assignee`：任务处理人（若未给出，默认当前执行人）
- `plan_review_result`：计划审阅结果（通过/需修改）
- `plan_worklog_hours`：生成 plan 实际耗时（用于 worklog）

## 标准流程

### Step 1 - 创建 Jira 并关联 PR
- 基于 `p4_key` 创建新任务（命名格式建议：`PR-XXXX`）。
- 自动设置：
  - 任务处理人 = 用户指定值（默认当前执行人）
  - 报告人 = 用户指定值（默认请求方）
  - 完成时间 = 下周五
  - `Original Estimate`、`Remaining Estimate` 留空
  - `Start Date`、`Target Date` 留空
- 建立 PR 与该 Jira 的关联关系。
- 输出：`jira_key`、`jira_url`、`assignee`、`reporter`、`due_date`。

### Step 2 - 基于远程 develop 创建分支
- 执行规范：
  - 同步远程：`git fetch origin`
  - 切换远程基线：`origin/develop`
  - 新建分支：`feature/PR-XXXX`（XXXX 来自 Step 1）
- 若本地存在同名分支，先校验是否允许复用；默认不覆盖。
- 输出：`branch_name` 与当前 HEAD 信息。

### Step 3 - 生成初版开发计划（供审阅）
- 结合 `requirement_doc` + 项目上下文生成 `docs/plan/YYYYMMDD_PR-XXXX_plan.md`。
- 强制包含以下结构：
  - 背景与目标
  - 范围（In Scope / Out of Scope）
  - 最小可执行任务单元拆解（按文件/模块/接口/校验点）
  - 风险与依赖
  - 验证策略（自测、回归、边界）
  - Checklist（可勾选）
  - 初步 Vibe Coding 工时估算（总工时 + 分项）
- 输出：计划文件路径与摘要，等待用户审阅。

### Step 4 - 审阅通过后落库与工时回填
- 若 `plan_review_result = 通过`：
  1. 提交 `plan` 到当前分支；
  2. 将 Jira 的 `Original Estimate` 与 `Remaining Estimate` 更新为 plan 总预计工时；
  3. 追加 comment，说明本次 plan 产出摘要；
  4. 新增 worklog，描述“生成 plan”耗时（`plan_worklog_hours`）。
- 若 `plan_review_result = 需修改`：
  - 回到 Step 3 迭代，不提交、不回填工时。

## 输出物
- Jira 任务信息（key/url/处理人/报告人/完成时间）
- 分支信息（feature/PR-XXXX）
- 计划文档：`docs/plan/YYYYMMDD_PR-XXXX_plan.md`
- 提交记录（仅审阅通过后）
- Jira 工时更新与 worklog 记录

## 约束与异常处理
- 未提供 `p4_key` 或需求文档：流程中止并提示缺失项。
- 远程 `develop` 不存在：流程中止并提示仓库基线异常。
- Jira 权限不足：保留本地 plan 产物，输出待人工补录字段。
- 工时字段不可写：写入 comment 作为兜底。

## 命令模板（PowerShell）
- `git fetch origin`
- `git checkout -b feature/PR-XXXX origin/develop`
- `git add docs/plan/YYYYMMDD_PR-XXXX_plan.md`
- `git commit -m "docs(plan): add YYYYMMDD_PR-XXXX initial plan"`

## 成功判定
- 具备 Jira + 分支 + plan 三件套；
- 计划可直接进入开发；
- 审阅通过后，工时字段与 worklog 完整落地。
