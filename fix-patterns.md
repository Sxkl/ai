# 修复模式知识库 (Fix Patterns)
积累于 2026-05-15 | 持续更新

## 决策模式

### DECISION-000: 禁止自动合并到 master (硬性规则)
- **特征**: 任何涉及 merge to master 的操作
- **判决**: 永久 REJECT — MR 仅创建，合并必须人工执行
- **原因**: 防止未经审核的代码进入生产主干
- **优先级**: 最高，不可被任何其他规则覆盖

### DECISION-001: 低错误量无代码变更
- **特征**: 错误量 < 1000/周，且均为上游/配置问题
- **判决**: APPROVE — 直接标注不可修复原因，不创建 MR
- **复用条件**: GetHistograms count < 1000 && 所有错误分类为 UPSTREAM/CONFIG

### DECISION-002: 共享根因多服务
- **特征**: 多个服务出现同一错误模式
- **判决**: 创建独立 Jira 但标注共享根因，统一修复点
- **复用条件**: >= 2 服务出现相同 exception class + message

## 不可修复原因标签

| 标签 | 含义 | 示例 |
|------|------|------|
| UPSTREAM | 上游/下游服务问题 | Feign 404, BBC 返回失败 |
| CONFIG | 配置/环境问题 | datasource URL 错误, 环境变量缺失 |
| DATA | 数据问题 | 无效用户ID, 重复数据 |
| DEPENDENCY | 依赖版本不兼容 | SalesOrderBillingEvent 类型转换失败 |
| BUSINESS | 业务逻辑预期内 | 审批不属于当前服务 |
| UNKNOWN | 无法确定根因 | NPE 无堆栈信息 |

## 修复模式

### 级别对照
| 级别 | 轮次 | 修复模式 | 示例 |
|:--:|:--:|------|------|
| L1 | 3 | FIX-001 Jackson, FIX-003 Logger null, FIX-004 printStackTrace, log_level, null_check, annotation_add | @JsonIgnoreProperties |
| L2 | 4 | retry_logic, exception_handling, serializer_fix, defensive_coding | Feign null guard |
| L3 | 5 | FIX-002 parallelStream NPE, lock_fix, thread_safety, business_logic, data_flow | Lua lock script |

### FIX-001: Jackson UnrecognizedField (L1 → 3轮)
- **症状**: `Unrecognized field "X", not marked as ignorable`
- **修复**: `@JsonIgnoreProperties(ignoreUnknown = true)` 在实体类
- **置信度**: 0.98
- **案例**: sim-service ServiceResource.soId

### FIX-002: parallelStream NPE (L3 → 5轮)
- **症状**: `NullPointerException` in `ForkJoinTask` from `.parallelStream().forEach()`
- **修复**: 在 parallelStream 前加 null/empty 检查
- **置信度**: 0.90
- **案例**: iot-contract UpdateContractServiceImpl

### FIX-003: Logger e.getMessage() null (L1 → 3轮)
- **症状**: `log.error("...{}", e.getMessage())` 输出 null
- **修复**: 改为 `log.error("msg", param1, param2, e)` 参数化日志
- **置信度**: 0.95
- **案例**: contract-service MnoGatewayCommonListener

### FIX-004: e.printStackTrace() (L1 → 3轮)
- **症状**: catch 块中使用 e.printStackTrace()
- **修复**: 改为 SLF4J 参数化日志 `log.error("msg", e)`
- **置信度**: 0.98

### FIX-005: log.error → log.warn (L1 → 3轮)
- **症状**: 正常业务状态报了 ERROR 级别
- **修复**: 降级为 log.warn
- **置信度**: 0.99
- **案例**: iot-order ProcessCycleSwitchRequest

### FIX-006: Cursor-based dedup for data pipelines (L2 → 4轮)
- **症状**: 数据管道重复处理导致数据不一致
- **修复**: 使用外部存储(DB/Airflow Variables)记录处理游标，仅在前序操作成功后推进
- **置信度**: 0.92
- **来源**: platform/airflow-dags sls__probe__platform_v4_probe__exception_aggregator
- **模式**: Variable.set(cursor_key, str(to_time)) 仅在 PutLogs 成功后调用

### FIX-007: Secrets externalization via 1Password reference (L1 → 3轮)
- **症状**: 配置文件中硬编码密码/Token
- **修复**: 替换为 `<see 1P:Vault/Item/Field>` 占位符，运行时通过 `op read` 注入
- **置信度**: 0.99
- **来源**: platform/eng-infra/* README 模式

### FIX-008: SLS index not ready retry (L2 → 4轮)
- **症状**: SLS GetLogs 返回 is_completed()=false
- **修复**: raise RuntimeError 触发 Airflow 重试，不更新游标确保无数据丢失
- **置信度**: 0.95
- **来源**: platform/airflow-dags exception_aggregator

### FIX-009: IaC as documentation (L1 → 3轮)
- **症状**: 基础设施配置无版本控制，灾难恢复困难
- **修复**: Git 仓库存储 sanitized 配置 + README 含主机/端口/卷挂载/密钥/恢复步骤
- **置信度**: 0.97
- **来源**: platform/eng-infra/* 三件套模式 (compose+README+secrets)

### FIX-010: MCP connection auto-reconnect (L2 → 4轮)
- **症状**: MCP 服务器连接断开导致工具调用失败
- **修复**: MCP 连接池单例 + 自动重连 + 工具列表缓存 + 失败后 reconnect 重试
- **置信度**: 0.90
- **来源**: platform/stargate MCPManager

### FIX-011: Skills DAG idempotency (L2 → 4轮)
- **症状**: 技能重复执行导致副作用
- **修复**: 在技能定义中使用 idempotency_key 防止重复 + 状态机 pending→queued→running→done/error
- **置信度**: 0.93
- **来源**: platform/stargate SkillOrchestrator

### FIX-012: Fernet encryption for secrets (L1 → 3轮)
- **症状**: 数据库/app_settings 中明文存储密钥/Token
- **修复**: 使用 Fernet 对称加密存储敏感值，加密密钥永不轮换
- **置信度**: 0.99
- **来源**: platform/stargate core/encryption.py
