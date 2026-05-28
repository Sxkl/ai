---
name: production-incident-fix
description: 生产故障排查修复全流程。Use ONLY when user provides a P4/PR number and asks to fix production errors for a specific service by pulling SLS logs, analyzing errors, fixing code, running tests, creating Jira, and submitting MR. Trigger keywords: 生产报错、SLS日志分析、代码修复、PR-XXXX、hotfix、故障排查、P4.
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

## Agent 超时配置

| Agent | 超时 | OnTimeout | 说明 |
|-------|:---:|-----------|------|
| sls-agent (日志拉取) | 300s | WARNING + 重试1次 | SLS API 数据量大，允许较长等待 |
| analyze-agent (根因分析) | 120s | WARNING + 重试1次 | 代码搜索 + 推理 |
| fix-agent (代码修复) | 300s | WARNING + 重试1次 | 文件读写 + 多轮修改 |
| review-agent (代码审查) | 120s | WARNING + 重试1次 | 每轮审查独立计时 |
| test-agent (单元测试) | 600s | WARNING + 重试1次 | 编译 + 测试执行 |

**超时处理规则**:
- 超时后不执行 SKIP，标记 WARNING 并自动重试 1 次 (相同超时)
- 两次均失败 → 降级处理，记录详细错误日志，使用已获取的部分数据继续
- 关键 Phase (Jira创建/SLS日志/代码修复) 超时两次后 ABORT 而非 SKIP

## 自动触发入口 (由 sls-log-analysis 升级桥触发)

当从 `sls-log-analysis` 的 Confidence-Gated 升级桥自动触发时，接受以下参数并跳过冗余步骤:

### 自动触发参数

| 参数 | 来源 | 说明 |
|------|------|------|
| service | sls-log-analysis input | 服务名 |
| error_patterns | sls-log-analysis Agent 3 风险矩阵 | 满足 5 条件的 K0XX 列表 |
| logstore | sls-log-analysis input | SLS Logstore |
| from_iso | sls-log-analysis input | 日志起始时间 ISO |
| to_iso | sls-log-analysis input | 日志结束时间 ISO |
| auto_triggered | true | 标记为自动触发 |

### 自动触发时的步骤调整

| Step | 原有行为 | 自动触发行为 |
|------|---------|-------------|
| Step 1 (Git准备) | 完整 clone + checkout + 建分支 | **复用** sls-log-analysis 时的分支(如有)，或正常创建 |
| Step 2 (创建 Jira) | 创建新工单 | **追加评论** 到已有的 sls-log-analysis Jira 工单，标注 `[AutoFix 续]` |
| Step 3 (SLS 日志拉取) | 全新拉取 ERROR 日志 | **跳过** — 复用 sls-log-analysis 的 Agent 1-3 分析结果(`error_categories.json`) |
| Step 4 (DMS 验证) | 按需 | 同上按需 |
| Step 5 (生成分析) | 新建 MD | 在 sls-log-analysis 报告基础上追加修复章节 |
| Step 6-10 | 正常执行 | 正常执行（代码修复/审查/测试/MR/Jira更新） |

### 自动触发降级规则

自动触发在任何 Step 失败时:
- 记录失败原因到 Jira comment
- **不**回滚已完成步骤
- **不**自动重试（非工作时间不重试，工作时间最多重试 1 次）
- 通知用户手动接管

### 恢复/从断点续跑

自动触发失败后的手动恢复:
- 用户输入: `继续修复 {service} --from-step=N`
- 系统读取 checkpoint 跳过已完成步骤
- 详见 §断点续传

## 断点续传机制

### Checkpoint 文件
- 存储位置: `~/.opencode/checkpoints/{pipeline_id}.json`
- pipeline_id 格式: `{Jira编号}-{service}-{启动时间ISO}`
- 每个 Step 完成/失败时自动写入

### Checkpoint 写入时机

| 触发条件 | 写入内容 | 原子性保证 |
|---------|---------|-----------|
| Step 成功完成 | step.status=completed, step.output, step.completed_at | 先写临时文件 `.tmp` → `mv` 原子替换 → 校验 JSON 完整性 |
| Step 失败 | step.status=failed, failure_reason, partial_data | 同上 |
| Step 跳过 (条件不满足) | step.status=skipped, reason | 同上 |
| 心跳超时 (30s 无响应) | 记录当前 step 的 partial_data + last_heartbeat | 每 10s 更新 heartbeat 字段 |

### Checkpoint 原子性校验 (防止脏 Checkpoint)

每次写入前:
1. 确认 `git status --porcelain` 无意外文件变更
2. 确认 `git log -1 --format='%H'` 与 base_commit 一致 (或存在预期 diff)
3. JSON schema 校验通过
4. 以上任一失败 → 标记 checkpoint 为 `untrusted`，写入失败原因

### 恢复流程

用户输入: `继续修复 {pipeline_id} [--from-step=N] [--force]`

恢复逻辑:
1. 读取 `~/.opencode/checkpoints/{pipeline_id}.json`
2. 校验 checkpoint integrity (JSON 完整 + 无脏标记)
3. 跳过所有 `status=completed` 的 Step
4. 从第一个 `status=pending` 或 `status=failed` 的 Step 继续
5. 若指定 `--from-step=N`: 强制将 Step N 及之前的 all 标记为 skipped，从 Step N 开始
6. 若指定 `--force`: 跳过 checkpoint integrity 检查 (危险，不推荐)
7. 恢复后的 Step 正常执行，写入新 checkpoint

### 恢复后的环境重建

恢复时需要重建的环境状态:
- **Git**: `git checkout {context_snapshot.base_commit}` → `git checkout -b {artifacts.branch}`
- **工作目录**: `cd {artifacts.repo_path}`
- **Jira 上下文**: 加载 `{artifacts.jira_key}` 的完整信息
- **SLS 数据**: 若 step_3 有 partial_data，从 `last_successful_offset` 继续

### 不可恢复的情况

| 情况 | 处理 |
|------|------|
| Checkpoint 文件丢失 | 从头重跑，输出 "checkpoint 丢失，全量重跑" |
| Checkpoint JSON 损坏 | 尝试修复→失败后从头重跑 |
| Git repo 被删除 | 重新 clone→跳过 step_1→从断点续跑 |
| Jira 工单被删除 | 重新创建 step_2，后续步骤正常续跑 |
| 依赖文件 (error_categories.json) 丢失 | 从 partial_data 重建或重新拉取 |

### 手动断点控制

用户可以在任何时候:
- `/checkpoint --list` — 列出所有 checkpoint
- `/checkpoint --show {id}` — 查看 checkpoint 详情
- `/checkpoint --delete {id}` — 删除指定 checkpoint
- `/checkpoint --force-step {id} {step_number}` — 强制标记某步骤为 completed
- `/checkpoint --reset-step {id} {step_number}` — 重置某步骤为 pending (重跑)

## Workflow Steps

### Step 1: Git 准备

1. Clone the service repo to workspace (if not already present)
2. Execute `git checkout master && git pull origin master` — ensure latest master code
3. Create work branch: `hotfix/{P4-编号}` (e.g. `hotfix/PR-6648`)

  **Checkpoint 写入 (Step 1)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_1_git_prepare", "completed", {branch, repo_path, base_commit})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_1_git_prepare", "failed", {reason, partial_data})`

### Step 2: 创建 Jira 工单

**重要**: 每次执行都必须创建全新 Jira 工单，绝不复用已有工单。

1. Use `stargate_jira_create_issue` to create a 任务 with:
   - `project_key`: "PR"
   - `summary`: `"[AutoFix][{service}] SLS生产报错分析 — {project}/{logstore} ({time_range})"`
   - `description`: 必须使用以下完整模板（替换 {} 占位符）:
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
     - [ ] GetIndex / GetHistograms / GetLogsV2 ERROR + Exception
     #### Phase 2: 数据库验证 (预计 3min, 条件触发)
     - [ ] pltdb_list_tables / search_columns / describe_table
     #### Phase 3: 根因分析 (预计 5min)
     - [ ] grep 源码 / 追踪调用链 / 修复方案
     #### Phase 4: 代码修复 (预计 10min)
     #### Phase 5: 三轮审查 (预计 10min)
     #### Phase 6: 单元测试 (预计 10min)
     #### Phase 7: 提交发布 (预计 3min)

     ### 📝 备注
     - 本工单由 OpenCode Multi-Agent 系统自动创建
     ```
   - `issue_type`: `"任务"`
   - `extra_fields`: `{"issuetype": {"id": "10113"}, "customfield_10456": "{截止日期+1天}", "customfield_10108": "{当前时间ISO格式}", "customfield_10109": "{当前时间+2h ISO格式}"}`
2. 创建成功后立即设置经办人和时间预估，Use `stargate_jira_update_issue`:
   - `extra_fields`: `{"assignee": {"name": "xiaokang.sun@linksfield.net"}, "timetracking": {"originalEstimate": "2h", "remainingEstimate": "2h"}}`
     *Jira Server/DC 的 assignee 必须传对象格式 {"name": "username"}*
3. Use `jira_jira_transition_issue` with `transition_id: "351"` (Start Work) → 状态变为"处理中"(执行中)
4. Use `jira_jira_get_sprints_from_board` to find the **current active sprint** on the project's board
5. Use `jira_jira_add_issues_to_sprint` to add the created issue to the active sprint
6. **注意**: 创建阶段不填 worklog 工时，只设置预估和计划时间。实际工时在 Step 10 回填时根据脚本实际执行时长填写。

  **Checkpoint 写入 (Step 2)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_2_jira_create", "completed", {issue_key, jira_url, sprint_id})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_2_jira_create", "failed", {reason, partial_data})`

### Step 3: SLS 日志拉取与错误分析

1. Calculate time range:
   - `from`: `date -v-1w +%s` (1 week ago Unix timestamp)
   - `to`: `date +%s` (current Unix timestamp)
2. Use `Sls-20201230-GetIndex` to check available index fields in the logstore
2a. 所有 SLS API 调用 (GetIndex/GetHistograms/GetLogsV2) 启用 3次指数退避重试:
     - 退避算法: base_delay=1s, max_delay=16s, backoff_multiplier=2, jitter=±25%
     - 可重试状态码: 429, 500, 502, 503, 504
     - GET 请求 (GetHistograms/GetLogsV2/GetProjectLogs) 全部可重试 (幂等)
     - 连续 5 次 ConnectionError → 标记 api_unreachable，使用已获取的部分数据继续
     - 超时处理: 单次 API 调用超时 → 标记 WARNING，自动重试 1 次 (相同超时)；两次均失败 → 降级并记录错误日志，使用已获取的部分数据继续
3. Use `Sls-20201230-GetHistograms` with query `"error OR Error OR ERROR OR exception OR Exception OR fail"` to get error distribution
4. Use `Sls-20201230-GetLogsV2` 分页拉取全部错误日志 (不限行数):
   - 使用 offset 分页: line=100, offset=0 → 100 → 200 ... 循环直到返回空
   - Query 1: `"ERROR" OR "Exception"` — 合并拉取所有错误和异常日志
   - **禁止使用固定 line 上限截断**, 必须拉取全部
5. 全量归集分类: 对每一条日志归类, 统计每种类型的次数/占比/严重程度
6. **知识库命中快速通道 (每个错误类型在进入5轮争论前执行)**:
   - **L1 精确命中 (conf ≥ 0.95)**: 已知模式精确匹配 → **跳过争论**，直接复用已知修复方案。在报告中标注"知识库命中, conf=X.XX, 跳过辩论，直接应用"
   - **L2 高置信命中 (conf ≥ 0.90)**: 模式高度相似 → **仅1轮确认** (正方+判决)，确认适用性后应用。标注"知识库高置信命中, conf=X.XX, 1轮快速确认"
   - **L3 未命中 (conf < 0.90)**: 走完整5轮争论 (R1正方→R2反方→R3反驳→R4最终→R5判决)，判决该错误是否可代码修复
   - 置信度直接使用知识库已有条目中的 conf 字段 (如 K001:0.98, K002:0.95)，无需额外计算
    - **冷启动优化**: 若 knowledge/services/{service}-knowledge.md 不存在，跳过知识库查询，所有类型直接走 L3 全流程
 7a. **会话缓存引用 (L1_CACHE)**:
    - 知识库内容 (fix-patterns.md + knowledge/index.md + known-services.yaml + decision-rules.yaml)
      已在会话启动时预加载到 L1 缓存 (~26K tokens)，无需每次 task() 重传
    - sub-agent 通过 `L1_CACHE(key='xxx')` 宏引用缓存条目:
      - `L1_CACHE(key='fix-patterns.md').match('FIX-001')` → 返回 FIX-001 的修复模板摘要
      - `L1_CACHE(key='knowledge/index.md').match('K001')` → 返回 K001 的关键信息
      - `L1_CACHE(key='known-services.yaml').service('sim-service')` → 返回服务配置
      - `L1_CACHE(key='decision-rules.yaml').rule('confidence-auto-merge')` → 返回规则条件
    - 若 sub-agent 无法访问 L1_CACHE（如第三方模型），自动降级为原上下文摘要策略
    - 缓存内容与源文件保持同步(file_change 触发刷新)
7. **上下文摘要策略**: 向 analyze-agent 传递 error_categories JSON 时，若某类型命中知识库:
   - 传知识库引用摘要 (K0XX: {标题}, conf={值}, 已知修复={一行摘要}) 而非内联完整知识条目
    - 未命中的类型正常传递 sample_log + context
 8. **知识库命中记录 (Librarian 钩子)**:
    - 每次知识库命中后，更新对应条目的 `last_hit_date` 和 `hit_count`:
      ```yaml
      # 在 knowledge/index.md 对应 K0XX 条目更新:
      last_hit: {ISO timestamp}
      hit_count: {hit_count + 1}
      ```
    - 修复完成后更新:
      ```yaml
      success: true/false
      success_count: {success_count + 1} (if success)
      fail_count: {fail_count + 1} (if fail)
      avg_fix_time: {平均修复耗时分钟}
      ```
    - 这些字段由 Knowledge-Librarian Agent 的 `freshness_check` 每日自动聚合到 `librarian-report-{date}.md`

  **Checkpoint 写入 (Step 3)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_3_sls_pull", "completed", {error_types_found, errors_pulled, last_successful_offset, last_successful_page})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_3_sls_pull", "failed", {reason, partial_data})`

### Step 4: DMS 数据库验证（可选）

If error logs contain `simIccid` or database-related fields:

1. Extract the `simIccid` values from error log context
2. Use `pltdb_describe_table` to view relevant table schemas
3. Use `pltdb_search_columns` to search for column name mismatches (e.g. `sim_iccid` vs actual column name)
4. Record findings — if column/table names mismatch, note the correct names

  **Checkpoint 写入 (Step 4)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_4_dms_verify", "completed", {findings})`
    - 跳过时: `write_checkpoint({pipeline_id}, "step_4_dms_verify", "skipped", {reason})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_4_dms_verify", "failed", {reason, partial_data})`

### Step 5: 生成分析文档

Create a markdown file `{P4编号}-error-analysis.md` in the workspace root containing:

```markdown
# {Service-Name} 生产环境错误分析与修复报告
- 需求编号 / 分析日期 / 日志来源 / 时间范围 / 错误总量

## 错误概览（表格：编号、类型、严重程度、频率、状态）

## 详细分析（每个错误：问题点、根因、典型日志、修复方案、测试方法）

## 修改文件清单

## 审查结果

## 测试建议

## 预期效果
```

  **Checkpoint 写入 (Step 5)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_5_analysis_doc", "completed", {analysis_doc_path})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_5_analysis_doc", "failed", {reason, partial_data})`

### Step 6: 代码修复

For each identified error category, locate the source file and apply the fix:

**Common fix patterns:**
- **Jackson unknown field deserialization**: Add `@JsonIgnoreProperties(ignoreUnknown = true)` on the entity class
- **Redis connection/pool**: Add retry mechanism, use `StringRedisTemplate` for string operations, use Lua scripts for atomic lock release
- **Feign NPE on null params**: Add `StringUtils.hasText()` guard before calling Feign methods, add null check on Feign results
- **ScheduledTask lock leak**: Ensure `finally` block always releases lock, handle `InterruptedException` properly
- **SQL column not found**: Verify column names against actual schema, fix mapping

**Rules:**
- Read each file before editing
- Follow existing code style patterns
- Use `edit` tool for modifications, preserve existing imports and annotations
- Add `log.warn`/`log.error` for failure paths

  **Checkpoint 写入 (Step 6)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_6_code_fix", "completed", {modified_files[], fix_summary})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_6_code_fix", "failed", {reason, partial_data})`

### Step 7: 三轮模型对抗审查

Launch 3 sequential adversarial review rounds using task agents:

**Round 1** — Basic Correctness: Compilation, imports, method signatures, type safety, API usage
**Round 2** — Thread Safety & Edge Cases: Race conditions, concurrency, null safety, resource leaks, serializer consistency
**Round 3** — Production Readiness: Regression risk, logging quality, final verdict

After each round, fix all identified issues before proceeding to the next round.

  **Checkpoint 写入 (Step 7)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_7_review", "completed", {review_result (3轮), issues_found[], issues_fixed[]})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_7_review", "failed", {reason, partial_data})`

### Step 8: 单元测试

1. Identify existing test files matching the modified source files (e.g. `*Test.java`)
2. Read test file structure and conventions to understand test patterns
3. Write/update unit tests covering:
   - **Happy path**: Normal flow works correctly
   - **Null/empty input**: Null and empty parameters handled gracefully
   - **Exception path**: Redis unreachable, Feign downstream failure handled
   - **Edge cases**: Lock contention, concurrent access, serializer consistency
4. Execute tests with `mvn test` or `./mvnw test`

  **Checkpoint 写入 (Step 8)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_8_test", "completed", {test_result, tests_passed, tests_failed})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_8_test", "failed", {reason, partial_data})`

### Step 9: 提交代码与创建 MR

1. Stage only the modified Java files (not .DS_Store, analysis docs, etc.):
   ```bash
   git add {file1}.java {file2}.java ...
   ```
2. Commit with message format: `"{P4编号} 修复生产环境报错: {简短描述}"`
3. Push to remote:
   ```bash
   git push -u origin {branch-name}
   ```
4. Create MR with `gh pr create` or provide direct GitLab MR URL:
   ```
    https://git.io.linksfield.net/{project}/-/merge_requests/new?merge_request%5Bsource_branch%5D={branch}&merge_request%5Btarget_branch%5D={target}
    ```

  **Checkpoint 写入 (Step 9)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_9_commit_mr", "completed", {commit_hash, mr_url, branch})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_9_commit_mr", "failed", {reason, partial_data})`

### Step 10: 更新 Jira

1. Use `jira_jira_transition_issue` with `transition_id: "311"` (Ready for QA) → 状态变为"核实中"(测试中)
2. Use `jira_jira_add_comment` 回填报告，**必须使用以下 8 段完整格式** (不可省略任何章节):
   ```markdown
   # {Service-Name} 生产环境错误分析与修复报告

   - 需求编号: {P4}
   - 分支: {branch}
   - 分析日期: {date}
   - 日志来源: {project}/{logstore} ({region})
   - 分析周期: {from} ~ {to}
   - 错误总量: ~{total} 条

   ## 一、问题总览 (表格: #/问题/严重程度/错误量/状态)

   ## 二、详细分析 (每问题: 问题点/修复方案/测试方法/修复文件)

   ## 三、修改文件清单 (表格: 文件/行变更/主要修复)

   ## 四、审查结果 (三轮审查表格: 轮次/发现数/关键问题/状态)

   ## 五、测试建议 (单元+集成)

   ## 六、预期效果 (修复前后对比)

   ## 七、遗留问题 (表格: 问题/状态/建议)

   ## 八、决策记录 (5轮多模型争论表格)

   ## 🔗 链接 (MR/Branch/Commit)
   ```
   - MR: {mr_url}
   - Branch: {branch}
   - Commit: {commit}

   ### ⚠️ 遗留问题
   - {unresolved}
   ```
3. Use `jira_jira_add_worklog` 回填实际工时（根据脚本实际执行时长计算）:
   - 先计算实际耗时: `bash date` 获取当前时间，减去 Step 2 记录的创建时间，得到实际运行时长
   - `time_spent`: 实际耗时 (e.g. `"5m"`, `"30m"`, `"1h 15m"`)
   - `started`: Step 2 创建时的实际开始时间 ISO 8601
   - `comment`: "完成：SLS日志分析 + 代码修复 + MR提交" 或实际做了什么
4. Attach the analysis MD document as a comment or file

  **Checkpoint 写入 (Step 10)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_10_jira_update", "completed", {transition_result, worklog_id})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_10_jira_update", "failed", {reason, partial_data})`

## Important Notes

- Only commit code files (`.java`), never commit analysis docs, `.DS_Store`, or config files unless explicitly requested
- When using SLS SQL queries, note that `content` field may not be indexed — use `GetLogsV2` with keyword search instead
- For Redis template fixes: prefer `StringRedisTemplate` for string operations rather than modifying global `setValueSerializer`
- For distributed lock release: use Lua scripts for atomic compare-and-delete to avoid race conditions
- Always verify there are no merge conflicts before creating MR
- If existing test files are present, check test conventions and follow the same patterns

## Safeguard Rules (不可移除的底线)

1. **串行执行保证**: Pipeline 各 Phase 严格串行执行 (Phase 1→2→3→...→VERIFY)，不存在多 Agent 并发修改同一文件的场景。文件保护依赖 git 自身版本控制而非外部锁机制。
2. **上下文摘要策略**: 向 sub-agent 传递知识库内容时，自动精简为摘要行 (K0XX: {标题}, conf={值}, 已知修复={摘要})，不内联完整知识条目。sub-agent 需通过摘要中的引用路径自行读取完整条目。
3. **超时容错**: 任何 Agent 超时后不执行 SKIP，而是标记 WARNING + 自动重试 1 次 (相同超时)。两次均失败 → 降级处理并记录详细错误日志。
4. **知识库置信度**: 知识库命中判断直接使用条目中的 conf 字段值，无需额外计算。无匹配条目时走完整分析流程。
5. **不可移除**: 以上 4 条规则在将来的任何优化中不得移除或弱化。
