---
name: sls-log-analysis
description: 全级别SLS日志自动梳理分析。拉取所有日志级别(INFO/WARN/ERROR)，使用5-Agent协作分类分析，识别异常模式、日志反模式和日志质量问题，生成日志健康报告并上传Jira。Use ONLY when user asks to scan logs, analyze all log levels, run log health checks, or do comprehensive log review. Trigger keywords: 日志梳理、log analysis、全级别扫描、日志健康、SLS分析、日志Review.
---

# 全级别 SLS 日志自动梳理分析（5-Agent 协作）

Automated comprehensive SLS log analysis using 5-agent collaboration:
SLS unified log pulling → multi-dimension classification → pattern analysis + quality audit → report generation → Jira upload.

**与 `production-incident-fix` 的区别**:
| 维度 | production-incident-fix | sls-log-analysis (本skill) |
|------|------------------------|---------------------------|
| 目标 | 修复生产代码 | 梳理日志质量 |
| 日志级别 | 仅 ERROR + Exception | INFO + WARN + ERROR (全级别) |
| 是否改代码 | 是 | 否（仅识别问题） |
| Agent 数 | 3 轮审查 | 5 Agent 协作 |
| 输出 | 修复报告 + MR | 日志健康报告 |
| Jira 摘要 | `[AutoFix]` | `[LogAnalysis]` |
| 触发词 | 生产报错/hotfix/P4 | 日志梳理/分析/扫描/健康 |

## Parameters (confirm with user before proceeding)

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| 服务 | No | 从已知服务列表选择 | 见 `shared/known-services.yaml` |
| P4/Jira 编号 | No | 自动生成 PR-XXXX | 分析报告工单编号 |
| SLS Project | No | uwp-prod | 从已知服务自动匹配 |
| SLS Logstore | No | 从已知服务自动匹配 | 首次扫描后自动注册 |
| SLS Region | No | cn-hongkong | SLS 地域 |
| 时间范围 | No | 1 week | 日志查询时间范围 |
| 分析深度 | No | 标准 | `快速`(仅ERROR+WARN) / `标准`(全级别) / `深度`(全级别+Eagle关联) |
| 责任人 | No | xiaokang.sun | Jira 的责任人 |

## Jira 自动创建配置（与 production-incident-fix 共享）

```
项目: PR (Engineering 4.x)
类型: 任务 (id: 10113)
必填字段: customfield_10456 (截止时间) = 创建日期+1天
负责人: xiaokang.sun@linksfield.net
Sprint: 自动查找当前 active sprint (board 30)
```

## 已知服务（共享配置）

服务列表存储在 `shared/known-services.yaml`，`production-incident-fix` 和 `sls-log-analysis` 共用同一份配置。

### 4.0 平台 (cube/platform/*)
| 服务 | SLS Logstore | 上次扫描 | 上次分析 |
|------|-------------|---------|---------|
| sim-service | k8s-newk8s-sim | 2026-05-16 | 2026-05-16 |
| contract-service | k8s-newk8s-contract | 2026-05-15 | - |
| customer-service | k8s-newk8s-customer | - | - |
| did-service | k8s-newk8s-did-service | - | - |
| event-center | k8s-newk8s-event-center | - | - |

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

用户只需输入服务名即可，所有参数自动匹配。新服务首次扫描后自动注册到共享配置。

## 增量扫描

再次扫描同一服务时，只拉取上次扫描时间之后的新增日志：

```
增量扫描 sim-service:
  ├─ 上次扫描: 2026-05-16 14:06
  ├─ 本次扫描: 2026-05-16 18:00
  ├─ 新增日志: xxx 条
  ├─ 新增错误类型: 0 (无新类型)
  ├─ 已有错误趋势: 错误1 ↓, 错误2 ✅ 已修复(0条)
  ├─ 日志质量评分: 82 → 85 (+3)
  └─ 自动更新 Jira PR-6677 评论

增量复用规则:
  - 若上次扫描 < 7 天 → 追加 comment 到同一 Jira
  - 若上次扫描 > 7 天或首次扫描 → 创建新 Jira
```

---

## 5-Agent 协作架构

```
                        ┌──────────────────────────────────┐
                        │      Agent 0: Orchestrator       │
                        │  (timing, handoff, merge, caps)  │
                        └──────────────┬───────────────────┘
                                       │
                        ┌──────────────▼───────────────────┐
                        │   Agent 1: SLS Unified Puller    │
                        │   ERROR → WARN → INFO (sequential)│
                        │   INFO 分层抽样 + noise-pre-filter│
                        └──────────────┬───────────────────┘
                                       │ structured logs JSON
                        ┌──────────────▼───────────────────┐
                        │   Agent 2: Log Classifier        │
                        │   6维分类 + noise-patterns匹配   │
                        └──────────────┬───────────────────┘
                                       │ classified data
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
    ┌─────────▼─────────┐    ┌────────▼────────┐              │
    │  Agent 3: Pattern │    │  Agent 4: Quality│              │
    │  Analyzer         │    │  Auditor (NEW)   │  ← 并行      │
    │  7项深度分析       │    │  对抗性审核       │              │
    └─────────┬─────────┘    └────────┬────────┘              │
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       │ merged analysis
                        ┌──────────────▼───────────────────┐
                        │   Agent 5: Report Generator      │
                        │   8段报告 + LQS + Jira上传        │
                        └──────────────────────────────────┘
```

### Agent 1: SLS Unified Puller

**职责**: 统一拉取所有级别的日志（顺序执行，避免 SLS API 争抢）。

**拉取顺序**: ERROR → WARN → INFO（从少到多，越重要的越先拉）

**INFO 分层聚合策略 (增强版)**:

| INFO 总量 | 策略 | 方法 |
|----------|------|------|
| < 50,000 | 全量拉取 | GetLogsV2(query=" INFO ", 分页) |
| 50,000 ~ 500,000 | SQL聚合 + 抽样 | **优先**: GetProjectLogs SQL聚合获取 Top10 Logger → **再**: GetLogsV2 各500条抽样 |
| > 500,000 | GetHistograms分布 + SQL聚合 + 极小抽样 | **Step A**: GetHistograms(query=" INFO ") 获取分钟级分布 → **Step B**: GetProjectLogs(group by logger, hour) 获取 Top5 Logger + 时间热点 → **Step C**: GetLogsV2(line=200) 仅拉单页代表性样本 |

**前置检查**: 使用 `GetIndex` 确认 `__content__` 字段已配置 SQL 分析索引。若未配置 → 直接 fallback 到旧分层抽样策略 (下方)。

**旧分层抽样策略 (fallback)**:
| INFO 总量 | 策略 |
|----------|------|
| < 50,000 | 全量拉取 |
| 50,000 ~ 500,000 | Top 10 Logger × 500条 抽样 |
| > 500,000 | Top 5 Logger × 200条 + 其余仅 distribution |

**要求输出格式**（预聚合，不传原始日志列表）:
```json
{
  "ERROR": {
    "total_count": 2341,
    "unique_loggers": 12,
    "unique_error_types": 5,
    "time_histogram": [{"hour": "2026-05-16T14", "count": 150}, ...],
    "top_patterns": [
      {
        "pattern_hash": "ServiceResource_UnrecognizedProperty",
        "count": 134,
        "sample_lines": ["...", "..."],
        "logger": "n.l.s.c.c.m.ServiceResourceListHandler",
        "thread_pools": ["cInvokePool", "Thread"]
      }
    ]
  },
  "WARN": { ... },
  "INFO": {
    "total_count": 5234000,
    "sampled": true,
    "sample_rate": "0.1%",
    "top_loggers": ["...", ...],
    ...
  }
}
```

**API 调用上限**（硬限制）:
- 每个级别 GetHistograms: 1 次
- 每个级别 GetLogs: 最多 50 页（5,000 条）
- 超过上限 → 标记 `"truncated": true`，报告声明覆盖率
- 总调用时间上限: 10 分钟/Agent

### Agent 2: Log Classifier

**职责**: 接收 Puller 输出，6 维分类 + 噪声标记。

**分类维度**:
1. **按日志级别**: ERROR / WARN / INFO 占比
2. **按模块/Logger**: Top 10 Logger 热度排序
3. **按错误类型**: Jackson/Redis/Feign/DB/NullPointer/超时/自定义
4. **按线程池**: `nio-80-exec-*`(HTTP) / `scheduling-*`(定时) / `cInvokePool-*`(异步)
5. **按频率**: 高频(>100次/h) / 中频(10-100) / 低频(<10)
6. **按业务影响**: 用户可见(>影响用户请求) / 系统内部

**噪声过滤**: 应用 `noise-patterns.yaml` 规则，匹配的日志标记 `[已过滤]`，不计入有效信号。

**输出格式**:
```
## 分类统计
| 维度 | 分类 | 数量 | 占比 | 趋势 |
|------|------|-----:|:---:|:---:|
| 级别 | ERROR | 2,341 | 0.04% | ↓ |
| ... | ... | ... | ... | ... |

## Top 10 Logger 热度
| Logger | ERROR | WARN | INFO | 总计 |
|--------|------:|-----:|-----:|-----:|
| ... | ... | ... | ... | ... |
```

### Agent 3: Pattern Analyzer

**职责**: 在分类基础上执行 7 项深度分析。

**分析清单**:
1. **异常趋势**: 各指标是否恶化（对比增量数据）
2. **日志反模式检测**:
   - 无堆栈的 ERROR（`log.error(msg)` 无 `e` 参数）
   - null 消息日志（`log.error("{}", e.getMessage())` 输出 `null`）
   - 级别误用（本该 DEBUG 却用 WARN/INFO）
   - 空 catch 块（catch 后无任何日志）
   - 敏感数据泄漏（password/token/secret/iccid 出现在日志中）
3. **时序聚类**: 突发峰值（某分钟 > 均值 ×3）
4. **关联分析**: WARN → ERROR 因果链
5. **周期性检测**: 固定时间点爆发
6. **频率异常**: 增长速率 > 50%/周 标记 ⚠️
7. **风险评分**: `risk_score = clamp(frequency(1-4) × severity(1-4) × novelty(1.0或2.0), 1, 10)`

**风险评分公式**:
| 频率分 | 条件 | 严重分 | 条件 | 新出现 | 乘数 |
|:---:|------|:---:|------|:---:|:---:|
| 1 | <10次/周 | 1 | 纯INFO噪音 | 是 | ×2.0 |
| 2 | 10-100次/周 | 2 | WARN可忽略 | 否 | ×1.0 |
| 3 | 100-1000次/周 | 3 | WARN需关注 | | |
| 4 | >1000次/周 | 4 | ERROR影响用户 | | |

### Agent 4: Quality Auditor (NEW)

**职责**: 对抗性审核，验证 Agent 2 和 Agent 3 的分析准确性。

**审核清单**:
1. **抽样验证**: 随机抽取 10% 日志，人工对比 Classifier 的分类结果
2. **遗漏检测**: 检查是否有日志不属于任何已知分类
3. **噪声规则验证**: 确认噪声过滤规则未误杀真实错误
4. **一致性检查**: 对比 Classifier 和 Pattern Analyzer 的结论，标记冲突
5. **覆盖率检查**: 确认拉取的样本足以支撑分析结论

**输出**: 审核报告 + 修正建议。审核不通过 → 标记 "⚠️ 低置信度"。

### Agent 5: Report Generator

**职责**: 汇总前 4 个 Agent 输出，生成 8 段完整报告 + 上传 Jira。

**日志质量评分公式** (LQS, 0-100):
```
LQS = ErrorHealth(0-40) + WarnQuality(0-20) + InfoSNR(0-20) - AntiPatternPenalty(0-20)
  - ErrorHealth:   40 - clamp(error_rate*1000, 0, 40)
  - WarnQuality:   20 - clamp(false_positive_ratio*100, 0, 20)  
  - InfoSNR:       clamp(actionable_info_ratio*100, 0, 20)
  - AntiPattern:   anti_pattern_count × 2, max 20
```

**评分等级**:
| LQS | 等级 | 含义 |
|:---:|:---:|------|
| 90-100 | 🟢 A | 日志健康，低噪音 |
| 70-89 | 🟡 B | 有改进空间 |
| 50-69 | 🟠 C | 需要优化 |
| <50 | 🔴 D | 日志质量问题严重 |

## Agent 超时配置

| Agent | 超时 | OnTimeout | 说明 |
|-------|:---:|-----------|------|
| Agent 1 (SLS 日志拉取) | 300s | WARNING + 重试1次 | SLS API 数据量大，允许较长等待 |
| Agent 2 (日志分类) | 120s | WARNING + 重试1次 | 分类处理 |
| Agent 3 (模式分析) | 120s | WARNING + 重试1次 | 7项深度分析 |
| Agent 4 (质量审核) | 120s | WARNING + 重试1次 | 对抗性审核 |
| Agent 5 (报告生成) | 180s | WARNING + 重试1次 | 报告生成 + Jira上传 |

**超时处理规则**:
- 超时后不执行 SKIP，标记 WARNING 并自动重试 1 次 (相同超时)
- 两次均失败 → 降级处理，记录详细错误日志，使用已获取的部分数据继续
- 关键 Phase (日志拉取) 超时两次后 ABORT

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
- **SLS 数据**: 若 step_2 有 partial_data，从 `last_successful_offset` 继续

### 不可恢复的情况

| 情况 | 处理 |
|------|------|
| Checkpoint 文件丢失 | 从头重跑，输出 "checkpoint 丢失，全量重跑" |
| Checkpoint JSON 损坏 | 尝试修复→失败后从头重跑 |
| Git repo 被删除 | 重新 clone→跳过 step_1→从断点续跑 |
| Jira 工单被删除 | 重新创建 step_1，后续步骤正常续跑 |
| 依赖文件丢失 | 从 partial_data 重建或重新拉取 |

### 手动断点控制

用户可以在任何时候:
- `/checkpoint --list` — 列出所有 checkpoint
- `/checkpoint --show {id}` — 查看 checkpoint 详情
- `/checkpoint --delete {id}` — 删除指定 checkpoint
- `/checkpoint --force-step {id} {step_number}` — 强制标记某步骤为 completed
- `/checkpoint --reset-step {id} {step_number}` — 重置某步骤为 pending (重跑)

### Step Key 映射

| Step | Checkpoint Key | 关键 output |
|------|---------------|-------------|
| Step 1 | `step_1_jira_create` | issue_key, jira_url |
| Step 2 | `step_2_sls_pull` | error_counts, last_successful_offset |
| Step 3 | `step_3_classify` | classified_data, top_loggers |
| Step 4 | `step_4_analyze_audit` | pattern_report, quality_report |
| Step 5 | `step_5_report_generate` | report_path, lqs_score |
| Step 6 | `step_6_jira_upload` | transition_result, worklog_id |

## Workflow Steps (6 Steps)

### Step 1: 创建 Jira 分析工单

**重要**: 首次扫描创建新工单；7天内增量扫描追加评论到同一工单。

1. Use `stargate_jira_create_issue`:
   - `project_key`: "PR"
   - `summary`: `"[LogAnalysis][{service}] SLS全级别日志梳理 — {project}/{logstore} ({time_range})"`
   - `description`:
     ```
     ## 📊 SLS 全级别日志自动梳理 — {service}

     ### 📋 基本信息
     | 字段 | 值 |
     |------|-----|
     | 服务名称 | {service} |
     | 代码仓库 | {repo_url} |
     | SLS Project | {project} |
     | Logstore | {logstore} |
     | Region | {region} |
     | 时间范围 | {from_date} ~ {to_date} (7天) |
     | 分析深度 | {depth} |
     | 责任人 | {assignee} |
     | 预计工时 | 1.5h |
     | 计划开始 | {current_time} |
     | 计划结束 | {current_time + 1.5h} |
     | 截止时间 | {current_date + 1d} |

     ### 🤖 5-Agent 分析流程
     #### Phase 1: 日志拉取 (Agent 1)
     - [ ] SLS Unified Puller: ERROR → WARN → INFO
     #### Phase 2: 分类与分析 (Agent 2-4, 并行)
     - [ ] Agent 2: 6维分类 + 噪声过滤
     - [ ] Agent 3: 7项模式分析 + 风险评分
     - [ ] Agent 4: 对抗性质量审核
     #### Phase 3: 报告生成 (Agent 5)
     - [ ] Agent 5: 8段报告 + LQS评分 + Jira上传

     ### 📝 备注
     - 本工单由 OpenCode 5-Agent 系统自动创建
     - 噪声过滤: noise-patterns.yaml
     ```
   - `issue_type`: `"任务"`
   - `extra_fields`: `{"issuetype": {"id": "10113"}, "customfield_10456": "{截止日期+1天}", "customfield_10108": "{当前时间ISO格式}", "customfield_10109": "{当前时间+1.5h ISO格式}"}`

2. 设置经办人 + 预估: `stargate_jira_update_issue` → `extra_fields: {"assignee": {"name": "xiaokang.sun@linksfield.net"}, "timetracking": {"originalEstimate": "1.5h", "remainingEstimate": "1.5h"}}`
3. 过渡: `jira_jira_transition_issue` → `transition_id: "351"` (Start Work → 处理中)
4. Sprint: `jira_jira_get_sprints_from_board`(board=30) → `jira_jira_add_issues_to_sprint`(active sprint)

  **Checkpoint 写入 (Step 1)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_1_jira_create", "completed", {issue_key, jira_url})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_1_jira_create", "failed", {reason, partial_data})`

### Step 2: SLS 日志拉取 (Agent 1)

1. 计算时间范围: `from=$(date -v-1w +%s)`, `to=$(date +%s)`
2. 索引检查: `Sls-20201230-GetIndex` → 确认 `line`/`content` 字段可用
2a. 所有 SLS API 调用 (GetIndex/GetHistograms/GetLogsV2/GetProjectLogs) 启用 3次指数退避重试:
    - 退避算法: base_delay=1s, max_delay=16s, backoff_multiplier=2, jitter=±25%
    - 可重试状态码: 429, 500, 502, 503, 504
    - GET 请求全部可重试 (幂等)
    - 连续 5 次 ConnectionError → 标记 api_unreachable，使用已获取的部分数据继续
    - 超时处理: 单次 API 调用超时 → 标记 WARNING，自动重试 1 次 (相同超时)；两次均失败 → 降级并记录错误日志，使用已获取的部分数据继续
3. 启动 Agent 1（统一拉取）:

```
task(description="Unified SLS log pull", subagent_type="sls-agent",
  prompt="拉取 {project}/{logstore} 的所有级别日志:
  1. ERRORS: GetHistograms(query=' ERROR ') → GetLogs 分页 (max 50页)
  2. WARNs:  GetHistograms(query=' WARN ') → GetLogs 分页 (max 50页)  
  3. INFOs:  GetHistograms(query=' INFO ') → 根据总量决策:
     - <50000 → full pull
     - 50000-500000 → Top10 Logger × 500
     - >500000 → Top5 Logger × 200 + distribution only
  
  输出: 结构化 JSON (total_count, unique_loggers, top_patterns[sample_lines],
  time_histogram, truncated flag)
  时间范围: {from}-{to}
  
  上下文策略: 使用 L1_CACHE 引用，不内联全文。
  - knowledge/index.md: L1_CACHE(key='knowledge/index.md')
  - fix-patterns.md: L1_CACHE(key='fix-patterns.md')
  - known-services.yaml: L1_CACHE(key='known-services.yaml')
  - noise-patterns.yaml: L1_CACHE(key='noise-patterns.yaml')
  若 L1_CACHE 不可用，降级为原始引用摘要传递。")
```

**API 约束**: 每级别最多 50 页，总时间上限 10 分钟。超时 → 标记 truncated。

  **Checkpoint 写入 (Step 2)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_2_sls_pull", "completed", {error_counts, last_successful_offset})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_2_sls_pull", "failed", {reason, partial_data})`

### Step 3: 日志分类 (Agent 2)

启动 Agent 2:

```
task(description="Classify logs", subagent_type="general",
  prompt="对 Agent 1 输出的日志数据进行 6 维分类:
  1. 按级别 (ERROR/WARN/INFO 占比)
  2. 按 Logger (Top 10)
  3. 按错误类型 (Jackson/Redis/Feign/DB/NPE/超时/自定义)
  4. 按线程池 (nio/scheduling/cInvokePool)
  5. 按频率 (高频>100/h / 中频10-100 / 低频<10)
  6. 按业务影响 (用户可见/系统内部)

  应用 noise-patterns.yaml 噪声过滤规则，匹配标记[已过滤]。

  输出: 4 张表格 + 每类代表性样本 (top 3 log lines)")
```

  **Checkpoint 写入 (Step 3)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_3_classify", "completed", {classified_data, top_loggers})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_3_classify", "failed", {reason, partial_data})`

### Step 4: 模式分析 + 质量审核 (Agent 3 + Agent 4 并行)

并行启动两个 Agent:

**Agent 3 (Pattern Analyzer)**:
```
task(description="Pattern analysis", subagent_type="general",
  prompt="对分类后的日志数据执行 7 项深度分析:
  1. 异常趋势 (vs 上次扫描)
  2. 日志反模式 (无堆栈/null消息/级别误用/空catch/敏感数据)
  3. 时序聚类 (突发峰值检测)
  4. 关联分析 (WARN→ERROR 因果链)
  5. 周期性检测
  6. 频率异常 (增长率 >50%/周 标记)
  7. 风险评分 (1-10, 频率×严重度×新出现)
  输出: 模式报告 + 风险矩阵")
```

**Agent 4 (Quality Auditor)**:
```
task(description="Quality audit", subagent_type="general",
  prompt="对分类和模式分析结果进行对抗性审核:
  1. 随机抽取 10% 原始日志，人工对比分类准确率
  2. 检查遗漏: 是否有日志无法归类?
  3. 验证噪声规则: 抽样检查 [已过滤] 日志，防止误杀
  4. 一致性: 对比 Agent 2 和 Agent 3 结论，标记冲突
  5. 覆盖率: 确认样本量足以支撑分析结论
  输出: 审核报告 + 置信度评级(高/中/低)")
```

  **Checkpoint 写入 (Step 4)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_4_analyze_audit", "completed", {pattern_report, quality_report})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_4_analyze_audit", "failed", {reason, partial_data})`

### Step 5: 报告生成 (Agent 5)

启动 Agent 5:

```
task(description="Generate report", subagent_type="general",
  prompt="汇总 Agent 1-4 的所有输出，生成 8 段完整报告:
  
  ## 一、日志总览
  - 级别分布表 (ERROR/WARN/INFO 数量+占比+趋势)
  - 模块热度矩阵 (Top 10 Logger 热力)
  - LQS 日志质量评分 (0-100) + 等级(A/B/C/D)
  
  ## 二、ERROR 详细分析
  - 类型/根因/影响范围/是否可代码修复
  - 每类附代表性日志样本 (top 3)
  
  ## 三、WARN 详细分析  
  - 类型/是否需要关注/降噪建议
  - 区分: [已过滤]正常行为 vs 需关注 WARN
  
  ## 四、INFO 异常 + 反模式清单
  - INFO 异常: DEBUG泄漏/噪音日志/缺失日志
  - 反模式: 无堆栈/null消息/级别误用/空catch/敏感数据
  - 每项标记是否存在
  
  ## 五、时序与关联分析
  - 突发峰值时间线
  - WARN→ERROR 因果链
  - 周期性规律
  
  ## 六、风险矩阵 + 改进建议
  - 风险矩阵表格 (1-10分, 高/中/低风险分类)
  - 改进建议 (优先级排序, actionable)
  - 日志存储成本估算 (可选)
  
  ## 七、日志质量评分详表
  - ErrorHealth/WarnQuality/InfoSNR/AntiPattern 子项得分
  - 与上次扫描对比 (如有)
  
  ## 八、增量对比
  - 首次扫描: N/A
  - 非首次: 各维度 DIFF + 趋势分析 + 新增/消除日志类型
  
  ---
  ## 建议升级到代码修复
  
  ### 升级条件评估（5 条件 AND 逻辑，缺一不可）
  
  | # | 条件 | 当前值 | 满足? | 来源 |
  |:--:|------|--------|:---:|------|
  | 1 | 风险评分 ≥ 7 | {max_risk_score}/10 | {✅/❌} | Agent 3 风险矩阵 |
  | 2 | 有已知 fix pattern | {pattern_ids} | {✅/❌} | knowledge/index.md 匹配 |
  | 3 | 错误量 ≥ 100/周 | {count}/周 | {✅/❌} | Agent 1 Puller 统计 |
  | 4 | 用户确认 APPROVE_FIX | 待确认 | ⏳ | gate-step 交互确认 |
  | 5 | 工作时间窗口(9:00-21:00 周一至周五) | {now_time} | {✅/❌} | decision-rules.yaml §business-hours |
  
  ### 高分风险项详情
  
  | # | 错误类型 | 风险 | 次数/周 | Fix Pattern | 可代码修复 | 满足升级条件? |
  |---|---------|:---:|------:|------------|:---:|:---:|
  | 1 | {type} | {risk} | {count} | {K0XX: title} | 是 | ✅ 全部满足 → 建议自动升级 |
  | 2 | {type} | {risk} | {count} | 无 | 未知 | ❌ 缺少 fix pattern → 需人工分析 |
  
  ### 自动升级决策
  
  {如果存在满足全部 5 条件的错误类型，输出以下块，否则跳过}
  
  > ⚡ **自动升级桥触发**: 以下 {N} 个错误类型满足全部 5 个升级条件。
  > 系统将在用户回复 `APPROVE_FIX` 后自动触发 `production-incident-fix` Skill。
  
  {对每条满足条件的错误类型}
  - **{type}**: risk={risk}, fix={K0XX}, count={count}/周
    → 自动触发命令: `对 {service} 执行 production-incident-fix --errors={K0XX} --from={from_iso} --to={to_iso}`
  
  {如果没有任何错误满足全部条件}
  > ℹ️ 当前无错误类型满足全部 5 个自动升级条件。如需手动修复，使用命令: `对 {service} 执行 production-incident-fix`
  
  ### 升级桥确认 (gate-step)
  
  当用户回复 `APPROVE_FIX` 后，系统自动执行以下流程:
  1. 加载 `production-incident-fix` Skill
  2. 传入参数: `service={service}`, `error_patterns=[{K0XX,...}]`, `logstore={logstore}`, `from={from_iso}`, `to={to_iso}`
  3. 跳过 Step 1 (Git 准备可复用分析时的 branch)
  4. 跳过 Step 3 (SLS 日志拉取，复用本次分析结果)
  5. 从 Step 5 (生成分析文档) 继续执行恢复流程
  6. 若用户回复 `REJECT_FIX` 或超时(5分钟无响应) → 分析报告仍保留在 Jira，不触发修复
  ---
  
  ## 🔗 链接
  - Jira: {jira_url}
  
  ## ⚠️ 质量审核
  - 审核置信度: {高/中/低}
  - 审核备注: {notes}
  ")
```

  **Checkpoint 写入 (Step 5)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_5_report_generate", "completed", {report_path, lqs_score})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_5_report_generate", "failed", {reason, partial_data})`

### Step 6: 上传 Jira

1. 过渡: `jira_jira_transition_issue` → `transition_id: "311"` (Ready for QA → 核实中)
2. 上传 MD 附件: `jira_jira_update_issue` → `attachments: "{report_path}"` + `fields: {"labels": ["LogAnalysis"]}`
   - 上传前检查大小: `ls -la {report}`, 若 >5MB 则截断样本至 top-3
3. 回填评论摘要:
   ```markdown
   ## 📊 日志健康分析完成 — {service}
   
   | 指标 | 值 |
   |------|-----|
   | 日志总量 | ~{total} |
   | 日志质量评分 | {lqs}/100 ({grade}) |
   | ERROR | {error}({error_rate}%) |
   | WARN | {warn} |
   | INFO | {info} |
   | 反模式 | {anti} 项 |
   | 高风险项 | {high_risk} 项 |
   
   ### {grade_icon} 日志质量: {grade} ({lqs}/100)
   
   ### 🔴 需关注
   {critical_items}
   
   ### 📎 完整报告见附件
   ```
4. 记录工时: `jira_jira_add_worklog`:
   - `time_spent`: 实际耗时（`date` 获取当前 - 创建时间）
   - `started`: Step 1 的创建时间
   - `comment`: "完成：SLS全级别日志梳理 + 5-Agent协作分析 + 报告生成"

  **Checkpoint 写入 (Step 6)**: 
    - 完成后: `write_checkpoint({pipeline_id}, "step_6_jira_upload", "completed", {transition_result, worklog_id})`
    - 失败时: `write_checkpoint({pipeline_id}, "step_6_jira_upload", "failed", {reason, partial_data})`

---

## 噪声过滤配置 (noise-patterns.yaml)

每个 Logstore 可配置已知噪声模式。技能目录下默认包含 `noise-patterns.yaml`:

```yaml
version: 1
# 全局通用噪声模式 (所有 Logstore 生效)
global:
  - regex: "es sim update get lock fail"
    reason: "ES定时任务多Pod竞争锁的正常行为"
    level: WARN
    auto_filter: true
    expires_after: 365d

  - regex: "HealthCheck.*timed? ?out"
    reason: "滚动发布时的临时探活超时，自恢复"
    level: WARN
    auto_filter: true
    expires_after: 365d

# 服务特定噪声模式
k8s-newk8s-sim:
  - regex: "bulk op response.*errors.*false"
    reason: "ES批量更新成功的正常响应日志"
    level: INFO
    auto_filter: true

k8s-newk8s-contract: []
```

**噪声规则维护**:
- 首次扫描后自动建议候选噪声模式
- Quality Auditor 每 30 天重新验证已有规则
- `expires_after` 到期自动降级为 `flag_only`
- 用户可手动编辑添加

---

## 两个 Skill 的协作关系

```
┌─────────────────────────────────────────────────────────────┐
│  用户: "扫描 sim-service"                                      │
│    ↓                                                         │
│  触发 sls-log-analysis (全级别梳理)                             │
│    → Agent 1-5 协作分析                                        │
│    → 生成日志健康报告 + Jira                                     │
│    → 报告末尾: 5条件评估 + 自动升级建议块                          │
│    ↓                                                         │
│  ┌─ 5条件全满足? ──YES──▶ gate-step: 等待用户 APPROVE_FIX        │
│  │                              ↓ 用户确认                     │
│  │                    自动触发 production-incident-fix           │
│  │                    复用 SLS 数据 + 跳过 Step 1/3              │
│  │                              ↓                              │
│  │                    代码修复 → 审查 → 测试 → MR → Jira更新       │
│  │                                                             │
│  └─ 5条件不满足? ─▶ 报告保留建议块，用户手动决定                    │
│                    → "对 sim-service 执行 production-incident-fix"│
│                    → 逐项修复                                   │
└─────────────────────────────────────────────────────────────┘
```

**明确分工**:
- `sls-log-analysis`: **只分析，不动代码**。输出"该修什么"的建议。
- `production-incident-fix`: **只修代码**。消费分析报告的建议或通过 Confidence-Gated 升级桥自动接收。
- **升级通过 5 条件 AND 逻辑控制**，满足全部条件 + 用户确认 `APPROVE_FIX` 后自动触发。

---

## Token / API 预算约束

| 约束项 | 上限 | 超限行为 |
|--------|:---:|------|
| SLS GetLogs 调用 | 50页/级别 | 标记 `truncated` |
| SLS 总执行时间 | 10min/Agent | 终止，用部分数据 |
| Agent 输入 context | ~50K tokens | 使用预聚合 JSON，不传原始日志 |
| 报告 MD 文件大小 | < 5MB | 截断样本行数 |

---

## Important Notes

- **预聚合优先**: Puller 输出统计摘要而非原始日志，避免 Agent 2-5 context 爆炸
- **Confidence-Gated 自动升级**: 报告建议升级，满足 5 条件 AND 逻辑(risk≥7 + 已知fix pattern + 错误量≥100/周 + 用户确认APPROVE_FIX + 工作时间窗口)后自动触发 `production-incident-fix`。不满足任何一条即不触发，仅保留建议块。
- **INFO 不全部拉取**: 一律走分层抽样，防止 API 成本爆炸
- **噪声先过滤**: 在 Classifier 阶段就标记已知噪声，避免干扰后续分析
- **空级别处理**: 若某级别 0 条日志，输出 `"✅ 无 ERROR 日志"` 而非空表
- **审核不通过**: Quality Auditor 标记 `"⚠️ 低置信度"`，建议人工复核
- **Sprint 必须 active**: 创建工单时确认当前有 active sprint，否则创建失败
