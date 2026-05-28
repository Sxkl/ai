---
name: dms-sql
description: 通过阿里云 DMS Enterprise 跑 SQL。当用户粘贴 SQL 语句(SELECT/SHOW/EXPLAIN)时触发。自动 schema → DbId 解析,通过 ExecuteScript 执行,结果以 markdown 表格返回。
---

# DMS SQL Skill

用户粘贴 SQL 时,通过阿里云 DMS Enterprise OpenAPI 用本机 OAuth profile 鉴权执行,结果渲染成 markdown 表格。

**铁律:** 默认只读。如果 SQL 含 `INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE`,**必须停下要用户明确确认**后才能执行。

---

## 用户必须先做好的前置

- 装 `aliyun` CLI ≥ 3.x(Mac 上 `brew install aliyun-cli`)
- 一次性 OAuth 登录: `aliyun configure --mode OAuth --profile dms`(浏览器 SSO)
- 验证: `aliyun sts GetCallerIdentity --profile dms` 返回 AccountId/Arn

如果 verify 失败,**不要继续**,告诉用户先修登录。

---

## 处理流程

### 步 1 — 从 SQL 提取 schema 名

解析第一个 `FROM <schema>.<table>`(也包括 `INTO <schema>.<table>` / `JOIN <schema>.<table>`)。
- `FROM cdr_aggregating.cdr_kettle_order_cycle_usage_t` → schema = `cdr_aggregating`
- `` FROM `db1`.`tbl` `` → schema = `db1`
- `FROM tbl`(无前缀)→ **询问**用户用哪个 schema,不要猜。

### 步 2 — 拿 Tid(本会话内缓存)

```bash
aliyun dms-enterprise GetUserActiveTenant \
  --endpoint dms-enterprise.aliyuncs.com --profile dms
```

从 JSON 读 `.Tenant.Tid`。会话内缓存复用。

### 步 3 — schema → DbId

```bash
aliyun dms-enterprise SearchDatabase \
  --Tid <TID> --SearchKey <SCHEMA_NAME> --PageSize 20 \
  --endpoint dms-enterprise.aliyuncs.com --profile dms
```

从 `.SearchDatabaseList.SearchDatabase[]` 挑 `SchemaName` 完全匹配的:
- 1 条 → 用 `.DatabaseId`。
- 多条(test + product 各一份)→ 用户没说优先 `EnvType: product`;否则**询问**用户按 Host/EnvType 选。
- 0 条 → 用户在 DMS 没该 schema 权限,告诉他找 DBA。

执行前先把映射告诉用户:
```
Schema cdr_aggregating → DbId 36048750 (host: rm-...:3306, env: product)
```

### 步 4 — 执行

```bash
aliyun dms-enterprise ExecuteScript \
  --Tid <TID> --DbId <DATABASE_ID> --Logic false \
  --Script "<USER_SQL>" \
  --endpoint dms-enterprise.aliyuncs.com --profile dms
```

SQL 安全引用。多语句用 `;` 分隔(DMS 每条返回一个 `Results[]`)。

### 步 5 — 结果渲染成 markdown 表格

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

每个 `Results[i]`:
```markdown
**Query #i** — RowCount: N

| col1 | col2 | ... |
|---|---|---|
| val | val | ... |
```

`Rows` 为空 → `(无数据)`。
外层 `Success: false` → 打印 `ErrorCode` / `ErrorMessage` / `RequestId`。

---

## 错误 → 处理

| 报错 | 处理 |
|---|---|
| `InvalidSecurityToken.Expired` | 跑 `aliyun sts GetCallerIdentity --profile dms` 刷新,重试一次 |
| `Forbidden.RAM` / `NoPermission` | RAM 没绑 DMS 权限,找 DBA |
| `unknown endpoint for dms-enterprise/<region>` | 漏了 `--endpoint dms-enterprise.aliyuncs.com`,补上重试 |
| 特定 schema Permission denied | 该用户在 DMS 对这个库无权限,DBA 授权 |
| 多个 `Results` | 多语句 SQL,每段单独渲染 |

---

## 硬性限制(不绕过)

- DMS 沙箱默认行数上限 200 + 读超时 7200s,不要人为加 `LIMIT`
- 单次 Script ≤ 1MB,超了拆
- 修改类 SQL 必须用户**同一对话里明确"yes run it"**确认才能跑,没确认就拒绝

---

## 完整示例

**用户粘:**
```sql
SELECT 'cdr_aggregating.cdr_kettle_order_cycle_usage_t' AS db_table,
       DATE(updated_at) AS d, COUNT(*) AS n,
       COUNT(DISTINCT sim_iccid) AS iccids
FROM cdr_aggregating.cdr_kettle_order_cycle_usage_t
WHERE updated_at >= '2026-03-01'
GROUP BY DATE(updated_at)
ORDER BY d DESC
LIMIT 30;
```

**Skill 流程:**
1. Schema = `cdr_aggregating`,SELECT,安全可跑。
2. `GetUserActiveTenant` → Tid(缓存)。
3. `SearchDatabase --SearchKey cdr_aggregating` → DatabaseId。
4. `ExecuteScript --DbId <id> --Script "..."` → JSON。
5. 渲染 markdown 表格。

**输出:**
```
Schema cdr_aggregating → DbId 36048750 (host: rm-...:3306, env: product)

Query #1 — RowCount: 30

| db_table | d | n | iccids |
|---|---|---|---|
| ... | 2026-04-25 | 12345 | 678 |
| ...
```
