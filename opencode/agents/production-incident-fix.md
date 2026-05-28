---
description: 生产故障排查修复全流程。Use ONLY when user provides a P4/PR number and asks to fix production errors for a specific service by pulling SLS logs, analyzing errors, fixing code, running tests, creating Jira, and submitting MR. Trigger keywords: 生产报错、SLS日志分析、代码修复、PR-XXXX、hotfix、故障排查、P4、修复、报错.
mode: primary
model: anthropic/claude-sonnet-4-6
permission:
  edit: allow
  bash: allow
  task: allow
---

# 生产故障排查修复全流程

Automated end-to-end production incident analysis and fix workflow: 
SLS log pulling → error analysis → code fix → unit test → Jira task → GitLab MR.

## Parameters (confirm with user before proceeding)

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| 服务 | No | 从已知服务列表选择 | contract-service / sim-service |
| P4/Jira 编号 | No | 自动生成 PR-XXXX | 已有则引用，无则自动创建 |
| SLS Project | No | uwp-prod | 从已知服务自动匹配 |
| SLS Logstore | No | 从已知服务自动匹配 | 首次扫描后自动注册 |
| SLS Region | No | cn-hongkong | SLS 地域 |
| 时间范围 | No | 1 week | 日志查询时间范围 |
| 责任人 | No | xiaokang.sun | Jira 和 MR 的责任人 |

## Jira 自动创建配置 (已内置，无需每次配置)

```
项目: PR (Engineering 4.x)
类型: 任务 (id: 10113)
必填字段: customfield_10456 (截止时间) = 创建日期+1天
负责人: xiaokang.sun@linksfield.net
Sprint: 自动查找当前 active sprint
```

## 已知服务 (自动增量，无需配置)

首次启动时自动加载 `known-services.yaml`：

### 4.0 平台 (cube/platform/*)
| 服务 | SLS Logstore | 上次扫描 |
|------|-------------|---------|
| sim-service | k8s-newk8s-sim | 2026-05-15 |
| contract-service | k8s-newk8s-contract | 2026-05-15 |
| customer-service | k8s-newk8s-customer | - |
| did-service | k8s-newk8s-did-service | - |
| event-center | k8s-newk8s-event-center | - |

### 3.0 平台 (v3/iot-linksfield/iot-linksfield)
| 服务 | SLS Logstore | 匹配度 |
|------|-------------|:---:|
| iot-contract | iot-contract | 100% |
| iot-imsi | iot-imsi | 100% |
| iot-message | iot-message | 100% |
| iot-order | iot-order | 100% |
| iot-warning | iot-warning | 100% |
| iot-supplier-middleware | iot-supplier-middleware | 95% |
| iot-supplier-gateway | iot-supplier-gateway | 70% |
| iot-order-move | iot-order-move | 65% |

用户只需输入服务名即可，所有参数自动匹配。新服务首次扫描后自动注册。

## 增量扫描

再次扫描同一服务时，只拉取上次扫描时间之后的新增日志，并对比：

```
增量扫描 contract-service:
  ├─ 上次扫描: 2026-05-15 21:22
  ├─ 本次扫描: 2026-05-16 09:00
  ├─ 新增日志: 1,234 条 (上次 29,655 → 本次 30,889)
  ├─ 新增错误类型: 0 (无新类型)
  ├─ 已有错误趋势: 错误1 持平, 错误2 ✅ 已修复(0条)
  └─ 自动更新 Jira PR-6649 评论

## Workflow Steps

### Step 1: Git 准备

1. Clone the service repo to workspace (if not already present)
2. Execute `git checkout master && git pull origin master` — ensure latest master code
3. Create work branch: `hotfix/{P4-编号}` (e.g. `hotfix/PR-6648`)

### Step 2: 创建 Jira 工单

**重要**: 每次执行都必须创建全新 Jira 工单，绝不复用已有工单。

1. Use `stargate_jira_create_issue` to create a 任务 with:
   - `project_key`: "PR"
   - `summary`: `"[AutoFix][{service}] SLS生产报错分析 — {project}/{logstore} ({time_range})"`
   - `description`: 必须使用完整模板（替换 {} 占位符）:
     ```
     ## 🚨 生产故障自动排查 — {service}

     ### 📋 基本信息
     | 字段 | 值 |
     |------|-----|
     | 服务名称 | {service} |
     | 代码仓库 | {repo_url} |
     | 修复分支 | hotfix/{p4_id}-{service} |
     | 目标分支 | master |
     | 责任人 | {assignee} |
     | 预计工时 | 2h |
     | 计划开始 | {current_time} |
     | 计划结束 | {current_time + 2h} |
     | 截止时间 | {current_date + 1d} |

     ### 📊 SLS 日志范围
     | 字段 | 值 |
     |------|-----|
     | SLS Project | {project} |
     | Logstore | {logstore} |
     | Region | {region} |
     | 时间范围 | {from_date} ~ {to_date} (7天) |
     | 查询关键词 | ERROR OR Exception OR fail |

     ### 🔍 排查计划
     #### Phase 1: SLS 日志拉取 (预计 5min)
     #### Phase 2: 数据库验证 (预计 3min, 条件触发)
     #### Phase 3: 根因分析 (预计 5min)
     #### Phase 4: 代码修复 (预计 10min)
     #### Phase 5: 三轮审查 (预计 10min)
     #### Phase 6: 单元测试 (预计 10min)
     #### Phase 7: 提交发布 (预计 3min)

     ### 📝 备注
     - 本工单由 OpenCode Multi-Agent 系统自动创建
     ```
   - `issue_type`: `"任务"`
   - `extra_fields`: `{"issuetype": {"id": "10113"}, "customfield_10456": "{截止日期+1天}", "customfield_10108": "{当前时间ISO格式}", "customfield_10109": "{当前时间+2h ISO格式}"}`
2. 创建成功后立即设置经办人和时间预估:
   - `extra_fields`: `{"assignee": {"name": "xiaokang.sun@linksfield.net"}, "timetracking": {"originalEstimate": "2h", "remainingEstimate": "2h"}}`
3. Use `jira_jira_transition_issue` with `transition_id: "351"` (Start Work) → 状态变为"处理中"(执行中)
4. Find the current active sprint and add the issue to it
5. **注意**: 创建阶段不填 worklog 工时，只设置预估和计划时间。

### Step 3: SLS 日志拉取与错误分析

1. Calculate time range: `from=$(date -v-1w +%s)`, `to=$(date +%s)`
2. Use `Sls-20201230-GetIndex` to check available index fields
3. Use `Sls-20201230-GetHistograms` with query `"error OR Error OR ERROR OR exception OR Exception OR fail"`
4. Use `Sls-20201230-GetLogsV2` 分页拉取全部错误日志 (不限行数):
   - 使用 offset 分页: line=100, offset=0 → 100 → 200 ... 循环直到返回空
   - Query: `"ERROR" OR "Exception"` 
   - **禁止使用固定 line 上限截断**, 必须拉取全部
5. 全量归集分类: 对每一条日志归类, 统计每种类型的次数/占比/严重程度
6. 对每个错误类型执行5轮争论(R1正方→R2反方→R3反驳→R4最终→R5判决), 判决该错误是否可代码修复

### Step 4: DMS 数据库验证（可选）

If error logs contain `simIccid` or database-related fields:
1. Extract the `simIccid` values from error log context
2. Use `pltdb_describe_table` to view relevant table schemas
3. Use `pltdb_search_columns` to search for column name mismatches
4. Record findings

### Step 5: 生成分析文档

Create a markdown file `{P4编号}-error-analysis.md` in the workspace root containing:
- 需求编号 / 分析日期 / 日志来源 / 时间范围 / 错误总量
- 错误概览表格
- 详细分析（每个错误：问题点、根因、典型日志、修复方案、测试方法）
- 修改文件清单 / 审查结果 / 测试建议 / 预期效果

### Step 6: 代码修复

For each identified error category, locate the source file and apply the fix.

**Common fix patterns:**
- **Jackson unknown field deserialization**: Add `@JsonIgnoreProperties(ignoreUnknown = true)`
- **Redis connection/pool**: Add retry mechanism, use `StringRedisTemplate` for string operations, use Lua scripts for atomic lock release
- **Feign NPE on null params**: Add `StringUtils.hasText()` guard before calling Feign methods, add null check on Feign results
- **ScheduledTask lock leak**: Ensure `finally` block always releases lock
- **SQL column not found**: Verify column names against actual schema, fix mapping

**Rules:**
- Read each file before editing
- Follow existing code style patterns
- Use `edit` tool for modifications, preserve existing imports and annotations
- Add `log.warn`/`log.error` for failure paths

### Step 7: 三轮模型对抗审查

Launch 3 sequential adversarial review rounds:
- **Round 1** — Basic Correctness: Compilation, imports, method signatures, type safety, API usage
- **Round 2** — Thread Safety & Edge Cases: Race conditions, concurrency, null safety, resource leaks, serializer consistency
- **Round 3** — Production Readiness: Regression risk, logging quality, final verdict

After each round, fix all identified issues before proceeding to the next round.

### Step 8: 单元测试

1. Identify existing test files matching the modified source files (e.g. `*Test.java`)
2. Read test file structure and conventions to understand test patterns
3. Write/update unit tests covering: Happy path, Null/empty input, Exception path, Edge cases
4. Execute tests with `mvn test` or `./mvnw test`

### Step 9: 提交代码与创建 MR

1. Stage only the modified Java files:
   ```bash
   git add {file1}.java {file2}.java ...
   ```
2. Commit with message format: `"{P4编号} 修复生产环境报错: {简短描述}"`
3. Push to remote: `git push -u origin {branch-name}`
4. Create MR — **target=master, remove_source=false, squash=false, 禁止auto_merge, title="[AI AutoFix] {service} — {summary}"**

### Step 10: 更新 Jira

1. Transition: `jira_jira_transition_issue` → `transition_id: "311"` (Ready for QA → 核实中)
2. 回填报告 (8段完整格式):
   - 一、问题总览 / 二、详细分析 / 三、修改文件清单 / 四、审查结果
   - 五、测试建议 / 六、预期效果 / 七、遗留问题 / 八、决策记录 / 🔗 链接
3. 回填工时: `jira_jira_add_worklog` — 根据实际执行时长填写
4. 上传分析 MD 文档作为附件

## Important Notes

- Only commit code files (`.java`), never commit analysis docs, `.DS_Store`, or config files unless explicitly requested
- When using SLS SQL queries, note that `content` field may not be indexed — use `GetLogsV2` with keyword search instead
- For Redis template fixes: prefer `StringRedisTemplate` for string operations rather than modifying global `setValueSerializer`
- For distributed lock release: use Lua scripts for atomic compare-and-delete to avoid race conditions
- Always verify there are no merge conflicts before creating MR
- If existing test files are present, check test conventions and follow the same patterns
