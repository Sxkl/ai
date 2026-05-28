---
name: dms-sql-cmd
description: 通过阿里云 DMS Enterprise (OAuth profile) 跑 SQL。用法: /dms-sql <SQL...>。自动 schema → DbId 解析,通过 ExecuteScript 执行,结果以 markdown 表格返回。
---

把用户在 `/dms-sql` 后面粘的 SQL 通过阿里云 DMS Enterprise OpenAPI 跑一遍。用本机 `dms` OAuth profile 鉴权,自动 schema → DbId 解析,通过 ExecuteScript 执行,结果以 markdown 表格返回。

**铁律:** 默认只读。如果 SQL 含 `INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE/REPLACE`,**必须停下,要求用户在下一条消息里明确输入"yes run it"** 后才能执行。

---

## 前置 — 跑之前先验

```bash
aliyun version | head -1
aliyun sts GetCallerIdentity --profile dms
```

如果 sts 失败,告诉用户先跑 `aliyun configure --mode OAuth --profile dms`(浏览器 SSO 登录),然后中断本次任务。

---

## 步 1 — 从 SQL 提取 schema 名

解析第一个 `FROM <schema>.<table>`(也包括 `INTO <schema>.<table>` / `JOIN <schema>.<table>`)。
- `FROM cdr_aggregating.cdr_kettle_order_cycle_usage_t` → schema = `cdr_aggregating`
- `` FROM `db1`.`tbl` `` → schema = `db1`
- `FROM tbl`(无 schema 前缀)→ **询问用户**用哪个 schema,不要猜。

## 步 2 — 拿 Tid(本会话内缓存)

```bash
aliyun dms-enterprise GetUserActiveTenant \
  --endpoint dms-enterprise.aliyuncs.com --profile dms
```

从 JSON 读 `.Tenant.Tid`。本会话内缓存,后续 query 直接复用。

## 步 3 — schema → DbId

```bash
aliyun dms-enterprise SearchDatabase \
  --Tid <TID> --SearchKey <SCHEMA_NAME> --PageSize 20 \
  --endpoint dms-enterprise.aliyuncs.com --profile dms
```

从 `.SearchDatabaseList.SearchDatabase[]` 里挑 `SchemaName` 完全匹配的:
- 1 条 → 用 `.DatabaseId`。
- 多条(比如 test + product 各一份)→ 用户没说就优先 `EnvType: product`;否则**询问用户**按 Host/EnvType 选。
- 0 条 → 用户在 DMS 里没该 schema 的权限,告诉他找 DBA 申请。

执行前先把解析结果显示给用户:
```
Schema cdr_aggregating → DbId 36048750 (host: rm-...:3306, env: product)
```

## 步 4 — 执行

```bash
aliyun dms-enterprise ExecuteScript \
  --Tid <TID> --DbId <DATABASE_ID> --Logic false \
  --Script "<SQL>" \
  --endpoint dms-enterprise.aliyuncs.com --profile dms
```

SQL 注意安全引用。多语句用 `;` 分隔也行(DMS 每条返回一个 `Results[]` 条目)。

## 步 5 — 结果渲染成 markdown 表格

响应结构:
```json
{
  "Success": true,
  "Results": [{
    "Success": true,
    "RowCount": 30,
    "ColumnNames": ["db_table","d","n","iccids"],
    "Rows": [{"db_table":"...","d":"2026-04-25","n":1234,"iccids":567}, ...],
    "Message": null
  }]
}
```

每个 `Results[i]` 渲染成:
```markdown
**Query #i** — RowCount: N

| col1 | col2 | ... |
|---|---|---|
| val | val | ... |
```

`Rows` 为空 → `(无数据)`。
外层 `Success: false` → 打印 `ErrorCode`、`ErrorMessage`、`RequestId`。

---

## 错误 → 处理

| 报错 | 处理 |
|---|---|
| `InvalidSecurityToken.Expired` | 跑 `aliyun sts GetCallerIdentity --profile dms` 强制刷新,重试一次 |
| `Forbidden.RAM` / `NoPermission` | RAM 用户没绑 DMS 权限,找 DBA 申请 |
| `unknown endpoint for dms-enterprise/<region>` | 漏了 `--endpoint dms-enterprise.aliyuncs.com`,补上重试 |
| 特定 schema 提示 Permission denied | 该用户在 DMS 里对这个库无权限,找 DBA 授权该库 |
| 多个 `Results` 返回 | 多语句 SQL,每段单独渲染 |

---

## 硬性限制(不绕过)

- DMS 沙箱默认行数上限(200)+ 读超时(7200s)— 不要人为加 `LIMIT`
- 单次 Script ≤ 1MB,超了拆
- 修改类 SQL 必须**用户在同一对话里明确输入"yes run it"**才能跑,没确认就拒绝

---

## 完整示例

用户输入: `/dms-sql SELECT 'cdr_aggregating.cdr_kettle_order_cycle_usage_t' AS db_table, DATE(updated_at) AS d, COUNT(*) AS n, COUNT(DISTINCT sim_iccid) AS iccids FROM cdr_aggregating.cdr_kettle_order_cycle_usage_t WHERE updated_at >= '2026-03-01' GROUP BY DATE(updated_at) ORDER BY d DESC LIMIT 30;`

Agent 流程:
1. 纯 SELECT → 安全可跑。
2. Schema = `cdr_aggregating`。
3. `GetUserActiveTenant` → Tid。
4. `SearchDatabase --SearchKey cdr_aggregating` → DatabaseId 36048750,env=product。
5. `ExecuteScript --DbId 36048750 --Script "..."` → JSON。
6. 渲染 markdown 表格。
