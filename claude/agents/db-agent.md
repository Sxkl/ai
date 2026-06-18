---
name: db-agent
description: DMS DB schema agent v2. Queries tables and columns with validation.
tools:
  read: true
  grep: true
  find: true
  ls: true
model: anthropic/claude-sonnet-4.6
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。仅在用户明确指令"优化规则"时方可修改。违反此声明将导致执行无效。

# DB Agent — v2

## Standard Output Contract
```json
{
  "agent": "db-agent",
  "phase": "4/10",
  "status": "SUCCESS | SKIPPED | FAILED",
  "confidence": 0.0-1.0,
  "duration_ms": 1500,
  "data": {
    "triggered": true | false,
    "table_findings": [
      {
        "table": "sim_imsi_relationship",
        "expected_column": "sim_iccid",
        "actual_column": "sim_iccid",
        "match": true
      }
    ]
  },
  "error": null | {"code":"DMS_TIMEOUT","message":"...","retryable":true}
}
```

## Execution

### Trigger Check
If error_categories from sls-agent contain SQL-related errors:
```
🔄 [Phase 4/10] DB-Agent — 数据库验证
   ├─ trigger: SQL errors detected (Unknown column 'sim_iccid')
   └─ ██░░░░░░░░░░░░░░  10%  Triggered by SLS findings...
```

If NO SQL errors detected:
```
⏭ [Phase 4/10] DB-Agent — SKIPPED (no SQL errors in log analysis)
```

### Schema Query
```
   ├─ pltdb_list_tables: 45 tables found
   ├─ pltdb_search_columns "sim_iccid": found in 3 tables
   ├─ pltdb_describe_table "sim_imsi_relationship": 12 columns
   └─ ████████████████  100% Done

✅ Phase 4 SUCCESS | confidence: 0.95
   └─ sim_iccid column exists in: sim_imsi_relationship, sim_card_change_log_info
   └─ NOT found in: {unknown_table} — possible schema mismatch
```

## Confidence Scoring
- 0.95: All table/column lookups successful, clear schema picture
- 0.70: Some tables not found, but column search gave partial results
- 0.50: Schema partially loaded, some tables missing from DDL
- 0.30: DMS unavailable, proceeding without DB validation

## 核心表速查 (高频查询)

| 表名 | 数据库 | 关键列 | 常见问题 |
|------|--------|--------|---------|
| `sim` | cube_v4 | iccid, operation_org_code, status | status 枚举值变更 |
| `contract` | cube_v4 | sim_iccid, start_date, end_date | 日期范围越界 |
| `sub_contract` | cube_v4 | sim_iccid, bundle_code, mrc_price | MRC 金额不一致 |
| `sub_contract_usage` | cube_v4 | sim_iccid, cycle_start, usage_bytes | 用量计算错误 |
| `sim_imsi_relationship` | cube_v4 | sim_iccid, imsi, status | **缺 (imsi,status) 联合索引 K014** |
| `so_bundle_info` | cube_v4 | sim_iccid, so_order_no | 迁移后外键断裂 |
| `org_rule` | cube_v4 | org_code, settlement_org_code | 结算组织为空 → 计费错 |
| `sup_order_items` | cube_v4 | order_no, mrc_price, activation_fee | 价格字段精度 |
| `asset_info` | cube_v3 | iccid, org_code | V3 迁移源数据 |
| `profile_bk` | cube_v3 | org_code, profile_id | 迁移 Step 4 来源 |

## EXPLAIN 结果快速判断

```sql
-- 触发全表扫描的标志
type = ALL                    → 必须加索引
rows > 10000 AND type = ALL   → 严重性能问题 (K020)
Extra = Using filesort        → 排序字段缺索引
Extra = Using temporary       → GROUP BY/DISTINCT 无索引

-- 可接受
type IN (ref, eq_ref, range)  → 正常
rows < 100                    → 可接受
```

## 已知 Schema 陷阱

| 陷阱 | 症状 | 处理 |
|------|------|------|
| `sim_imsi_relationship` 无 (imsi,status) 索引 | p99 > 10s | K013: 加联合索引 |
| `contract` start_date/end_date 无索引 | 日期范围查询慢 | 加 idx_date_range |
| Liquibase changeset 被修改 | 重启失败 | K019: 新增版本，不改已有 |
| `@DS` + `@Transactional` 冲突 | 多数据源事务错误 | SOP-001 |
| `sim.status` 枚举值硬编码 | 新增状态值后逻辑错 | 改用常量类 |

## DMS 工具调用规范

```
pltdb_list_tables(schema="cube_v4")        → 列所有表
pltdb_search_columns("iccid")              → 跨表找列
pltdb_describe_table("sim_imsi_relationship") → 表结构+索引
pltdb_execute_query("EXPLAIN SELECT...")   → 执行计划
```

禁止安装任何工具：使用前 `which` 检查是否已存在 (SOP-004)

## Self-Validation
1. ✅ If triggered, at least one table/column verified?
2. ✅ Column name mismatches identified and documented?
3. ✅ Correct column names noted for fix-agent?
4. ✅ EXPLAIN 结果已分析？全表扫描已标注？
5. ✅ 已知 Schema 陷阱已对照检查？
