<!-- Knowledge-Librarian 元数据块
  由 Knowledge-Librarian Agent 自动维护，手动编辑需谨慎
  
  last_librarian_run: 2026-05-18
  total_entries: 19
    active: 19
    stale: 0
    archived: 0
  duplicate_groups: 0
  next_freshness_check: 2026-05-19
  next_report: 2026-05-25
-->

# 知识库索引

扫描时先匹配此索引中的模式，命中后直接采用已知方案，减少裁决轮次。

## L1 简单 (3轮裁决)

| ID | 模式 | 匹配特征 | 修复模板 |
|----|------|---------|---------|
| K001 | Jackson未知字段 | `Unrecognized field.*not marked as ignorable` | `@JsonIgnoreProperties(ignoreUnknown=true)` |
| K002 | Logger null message | `log.error.*e.getMessage()` → 输出null | 参数化: `log.error("msg", param, e)` |
| K003 | e.printStackTrace | catch块 `e.printStackTrace()` | `log.error("msg", e)` |
| K004 | error降warn | 正常业务态报ERROR | `log.error`→`log.warn` |
| K005 | 空值null检查 | NPE from `xxx.xxx()` 无防御 | `if (x == null) { log.warn; return; }` |
| K012 | Secret硬编码 | 配置文件含密码/Token明文 | Fernet加密 或 1Password引用占位 |
| N001 | ES document_missing | `document_missing_exception` + update retry | `.docAsUpsert(true)` |

## L2 中等 (4轮裁决)

| ID | 模式 | 匹配特征 | 修复模板 |
|----|------|---------|---------|
| K006 | Feign null guard | `FeignException` + null参数 | `if (StringUtils.hasText(x))` 前拦截 |
| K007 | 响应null检查 | `restTemplate.postForObject` 无null判断 | 加 `if (response == null) return;` |
| K008 | serviceCycleCount空 | `serviceCycleCount为空` + fallback仍null | 二次null检查+默认值"0" |
| K010 | MCP连接断开 | MCP tool call timeout/connection error | 自动重连 + 工具列表重建 |
| K011 | 技能重复执行 | 相同技能并发跑导致副作用 | idempotency_key 幂等检查 |

## L3 复杂 (5轮裁决)

| ID | 模式 | 匹配特征 | 修复模板 |
|----|------|---------|---------|
| K009 | parallelStream NPE | `NullPointerException` in ForkJoinTask + `.parallelStream()` | 加null检查在parallelStream前 |
| K013 | Redis锁泄漏 | `Unable to connect.*Redis` + `deleteTaskLock` finally缺失 | Lua脚本原子释放 |
| K014 | 序列化不一致 | `SerializationException` + Redis valueSerializer | `setValueSerializer(stringSerializer)` |

## 不可修复模式

| ID | 模式 | 标签 | 说明 |
|----|------|------|------|
| U001 | BBC回调F | UPSTREAM | BBC上游返回操作失败 |
| U002 | Feign 404 | UPSTREAM | 下游端点不存在 |
| U003 | datasource路由 | CONFIG | @DS注解指向错误数据库 |
| U004 | SalesOrderBillingEvent | DEPENDENCY | billing-middleware版本不一致 |
| U005 | Authing无效用户 | DATA | 上游传入无效用户ID |

## 使用规则
1. 扫描SLS日志 → 提取错误特征 → 匹配此索引
2. 命中：直接应用已知修复方案，裁决从简(仅确认方案适用性)
3. 未命中：走完整裁决流程，修复后追加新条目到此索引
4. **新服务首次扫描**: 同时生成 `knowledge/services/{service}-knowledge.md`

## 服务知识库 (防止踩已知陷阱)

| 服务 | 文档 | 已知陷阱 |
|------|------|---------|
| contract-service | `services/contract-service-knowledge.md` | @Transactional+@DS冲突 / Redis连接池泄漏 / Zombie RedisMessageListenerContainer |
| stargate | `services/stargate-architecture.md` | MCP 连接池模式 / 技能系统 DSL / 3轮对抗审查 / Fernet 加密 |

## 标准处理流程 (SOP)

| SOP | 触发条件 | 文档 |
|------|---------|------|
| SOP-000 | 被动发现快速处理 | `patterns/SOP-000-manual-incident-response.md` |
| SOP-001 | @Transactional+@DS多数据源冲突 | `patterns/SOP-001-transactional-ds-conflict.md` |
| SOP-002 | K8s RollingUpdate Redis连接池耗尽 | `patterns/SOP-002-redis-pool-exhaustion.md` |

## Cost Tracking (v2.2)

每次修复后更新对应知识条目的 cost 字段:

| ID | 近期平均成本 | 最近执行 |
|----|----------:|------|
| K001 | — | — |

### Cost 记录格式
```yaml
# 在各自 K0XX.md 末尾追加:
## Cost History
| 日期 | 服务 | tokens_in | tokens_out | cost_usd | 效果 |
|------|------|----------:|----------:|------:|------|
| 2026-05-16 | cube-server | 8500 | 1200 | 0.042 | -100% |
```
