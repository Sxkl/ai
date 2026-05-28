---
name: "standard-requirement-dev-prep"
description: "Automates pre-development preparation from requirement doc + P4: create task, branch, initial plan, and effort updates. Invoke when user starts a new requirement implementation."
version: "1.0.0"
author: "linksfield"
---

# 标准需求开发前期准备 Skill

## 适用场景

当用户提供**需求文档**并给出 **P4 编号**时，触发本 Skill，执行“开发前期准备”全流程：

1. 创建并关联任务（PR-XXXX）。
2. 基于远程 develop 创建 feature 分支。
3. 生成初版开发计划（plan）并等待审阅。
4. 审阅通过后提交 plan，并回填工时与评论记录。
5. 全流程严格串行执行，任一步失败立即停止，不执行后续步骤。

---

## 输入约定

- 必填输入：
  - 需求文档（文本、链接或附件摘要）
  - P4 编号（示例：P4-5938）
- 默认规则：
  - 任务处理人 = 报告人 = 当前操作者
  - 任务完成时间 = 下周五
  - Start Date / Target Date 为空
  - 预计工时 / 剩余工时 初始为空，待 plan 审阅后回填

### Jira 字段映射（可配置模板）

优先使用以下映射，避免跨项目字段差异导致失败：

```yaml
jiraMapping:
  p4LinkField: "customfield_xxxx"
  estimateField: "timetracking.originalEstimate"
  remainingField: "timetracking.remainingEstimate"
  dueDateField: "duedate"
  assigneeField: "assignee"
  reporterField: "reporter"
```
字段缺失或不可写视为失败，立即停止流程。

### Jira 创建字段固定规则（PR 项目）

当项目为 `Engineering 4.x (PR)` 时，创建任务必须严格按以下字段：

- 项目：`PR`
- 问题类型：`任务`（强制映射 `issuetype.id=10113`）
- 概要：`<P4 概要> - 后端开发`
- 报告人：当前用户（默认）
- 截止时间：下周五（默认）
- 描述：创建时留空，plan 审阅通过后更新
- 优先级：`Medium`（默认）
- 链接的问题：`blocks` 指向输入的 P4（如 `P4-5220`）
- 经办人：当前用户（默认）
- 初始预估：留空，plan 审阅通过后更新
- 剩余的估算：留空，plan 审阅通过后更新
- Target start：留空
- Target end：留空
- 测试负责人：`yadong.liu@linksfield.net`（默认）

补充映射（来源于 Jira 创建页配置）：
- `PR`（projectId=`10264`）使用 issueType 配置组 `10695`
- 在配置组 `10695` 中：
  - `10113` = 任务
  - `10115` = 故事
  - `10116` = 故障
  - `10000` = Epic
- Jira QuickCreate（`/secure/QuickCreateIssue.jspa?decorator=none`）关键表单字段：
  - `pid=10264`
  - `issuetype=10113`
  - `priority=3`（对应 Medium）
  - `issuelinks=issuelinks`
  - `issuelinks-linktype=blocks`
  - `issuelinks-issues=P4-XXXX`
  - 仅当上述三项链接字段同时存在时，页面创建可一次性带出 linked issue。

---

## 执行步骤

### Step 0：预检查（新增）

1. 校验 P4 格式是否合法且可检索。
2. 校验 Jira 连接与认证是否可用（必须可创建任务）。
3. 校验 Jira 关键字段可写（P4 关联、处理人、报告人、Due Date）。
4. 检查远程 `origin/develop` 是否存在。
5. 若以上任一步失败，立即停止并输出失败原因，不执行 Step 1 及后续步骤。

### Step 1：创建任务并关联 P4

创建 Jira 任务并关联 P4，任务号必须由 Jira 创建结果返回（例如 `PR-6312`），并满足：

- 任务标题必须为“需求主题（P4-XXXX）- 后端开发”，不得出现“开发前期准备”等一次性阶段性措辞。
- 项目固定为 `Engineering 4.x (PR)`。
- 问题类型固定为 `任务`。
- 创建参数需显式使用 `issuetype.id=10113`（不可仅依赖文案“任务”）。
- 关联上游 P4。
- 关联方式必须落在 Jira「链接的问题（Linked Issues）」中（建议使用 `Blocks` 关系）。
- 指定处理人、报告人（同一人）。
- Due Date 设为下周五。
- 优先级固定为 `Medium`。
- 预计工时、剩余工时留空。
- Start Date、Target Date 留空。
- 测试负责人默认 `yadong.liu@linksfield.net`。
- 创建时 description 保持空（不预填）。
- 若创建失败或未返回有效任务号，立即停止流程。
- 若创建后未检测到有效的「链接的问题」关联（PR-XXXX ↔ P4-XXXX），立即停止流程，不进入 Step 2。
- 若“问题类型=任务”等用户硬约束无法满足，必须立即停止并向用户反馈失败原因、接口报错原文、已尝试参数；禁止降级为“故事”等其他类型继续创建。
- 若使用 `issuetype.id=10113` 仍失败，必须停止并反馈，不得继续 Step 2。
- 若通过 API 尝试补链返回成功但 `linkedIssues(P4-XXXX)` 校验仍为 0，视为补链失败，必须停止并反馈。

输出内容：

- 任务号（Jira 实际返回）
- 任务链接
- 处理人 / 报告人
- Due Date

### Step 2：创建开发分支

仅使用 Step 1 返回的任务号创建分支，不允许使用 P4 编号推断任务号。

从远程 develop 拉取并创建分支：

```bash
git fetch origin
git checkout -b feature/<Step1返回任务号> origin/develop
```

分支命名必须严格为：`feature/PR-XXXX`（其中 `PR-XXXX` 来自 Jira 创建结果）。
若目标分支已存在，视为流程冲突并立即停止（不复用历史分支）。

输出内容：

- 新分支名
- 分支来源（origin/develop）

### Step 3：生成初版 plan（待审阅）

基于需求文档 + 项目上下文，生成 `docs/plan` 下的计划文档：

- 路径：`docs/plan`
- 文件名：`YYYYMMDD_<Step1返回任务号>_plan.md`
- 内容要求：
  - 目标与范围
  - 影响模块与依赖
  - 最小可执行任务拆解（任务粒度可独立交付/验证）
  - Checklist（开发、联调、自测、回归）
  - 初步 vibe coding 工时估算（总工时 + 分项）
  - 工时拆分（开发 / 联调 / 自测）
  - 风险与回滚点

输出内容：

- plan 文件路径（可点击链接）
- plan 预计工时（用于后续回填）
- 请用户审阅确认

### Step 4：审阅通过后提交与回填

用户确认后执行：

1. 提交 plan 到当前分支（提交仅包含 plan 文件）。
2. 更新 PR-XXXX：
   - 预计工时 = plan 预计工时
   - 剩余工时 = plan 预计工时
3. 将 plan 精简版写入 Jira description（覆盖原 description）：
   - 仅保留：目标与范围、任务拆解摘要、总工时与拆分、关键风险与回滚点
   - 保持可读且可执行，避免粘贴完整长文
4. 追加备注（comment）：
   - 说明该 plan 的依据、范围、风险假设
5. 将“计划编制耗时”写入 Jira 评论：
   - 使用固定评论模板记录计划编制耗时与依据。

评论模板（固定）：

```text
开发计划已审阅通过：
- plan 文件：docs/plan/YYYYMMDD_PR-XXXX_plan.md
- 计划编制耗时：<Xh>
- 总预计工时：<Yh>（开发 <Ah> / 联调 <Bh> / 自测 <Ch> / 方案评审 <Dh>）
- 计划依据：需求文档 + 评审结论
```

提交信息建议：

```text
PR-XXXX docs: add initial development plan
```

### Step 4 执行门禁（新增）

仅在以下条件全部满足时执行提交与回填：

- 用户明确审阅通过。
- plan 中存在可解析“总预计工时”。
- 当前分支为 `feature/PR-XXXX`。
- `PR-XXXX` 与 Step 1 返回任务号完全一致。
- PR-XXXX 与 P4-XXXX 的「链接的问题」关联仍然存在。

若任一条件不满足，仅输出差异与待处理项，不提交、不回填。

---

## 输出模板

每次执行本 Skill，按以下结构输出：

1. 基础信息
   - P4 编号
   - PR-XXXX（必须为 Jira 新建返回）
   - 分支名
2. 产物清单
   - plan 文件路径
   - plan 预计工时
3. 审阅状态
   - 待审阅 / 已通过
4. 后续动作
   - 是否已提交
   - 是否已回填工时
   - 是否已写入固定评论模板

---

## 质量约束

- 不跳过“先审阅再提交”。
- plan 必须可执行，禁止只有概念性描述。
- 分支与任务号强绑定：`feature/PR-XXXX`，且任务号必须来自 Jira 新建结果。
- PR 标题必须是“需求主题（P4-XXXX）- 后端开发”。
- PR 创建时 description 必须为空；审阅通过后再写入精简版 plan 描述。
- P4 关联必须通过「链接的问题」建立，缺失则流程失败。
- 当 Jira 字段校验失败时，必须 Fail-Fast：立即停止并反馈，不允许自行改用其他字段值继续推进。
- 工时回填数值必须来源于 plan，不手工臆测。
- worklog 默认不再自动写入；必须在 Jira 评论中记录计划耗时。
- 提交前必须通过变更白名单校验：仅允许本任务相关文件。
- Jira 更新后必须二次读取校验 `description` / `timetracking` / `issuelinks`。
- plan 提交前执行 `snake_case` 请求字段扫描，不通过则禁止提交。
- 工时必须包含总量与分项（开发/联调/自测/方案评审）并与 Jira 回填一致。
- 禁止用 P4 编号推断 PR 任务号（例如禁止 `P4-5220 -> PR-5220`）。
- 若无法创建 PR，流程必须立即停止，不允许继续建分支或生成正式 plan 文件。
- 交互文档中与前端约定的请求参数（path/query/body）与返回字段必须统一为 `snake_case`。
- 业务语义仍可使用 `groupCode` 描述，但接口字段命名需落为 `group_code`。
