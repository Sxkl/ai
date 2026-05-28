# SOP-001: @Transactional + @DS 多数据源冲突 — 检测修复补偿全流程

> **版本**: v1.0 | **日期**: 2026-05-16 | **可复用**: ✅  
> **触发条件**: SLS 日志出现 `Table 'xxx.sim' doesn't exist` 或 `SQLSyntaxErrorException` 在 `@DS` 标记的表上  
> **知识库**: U003 (CONFIG) | K005 (null检查) | N003 (@Transactional+@DS冲突)

---

## Phase 1: SLS 检测 (自动)

### 特征日志
```
ERROR CancelActionServiceImpl : cancel error,errorMessage:
ERROR CancelBundleService : cancelBundle validate failed,{simIccid},{null}
Caused by: java.sql.SQLSyntaxErrorException: Table 'sphere2-contract.sim' doesn't exist
```

### SLS 查询
```
"cancel error" OR "doesn't exist" OR "SQLSyntaxErrorException"
```

### 诊断逻辑
```
if error contains "SQLSyntaxErrorException" + "doesn't exist":
    check if table name has @DS annotation in codebase
    if yes → SOP-001 (this flow)
    if no → check DBA (actual missing table)
```

---

## Phase 2: 根因确认 (自动)

### Step 1: grep @Transactional + @DS 冲突

```bash
# 找到所有 @Transactional 方法
grep -r "@Transactional" --include="*.java" {service-path}

# 找到所有 @DS 标注
grep -r "@DS(" --include="*.java" {service-path}

# 交叉分析: @Transactional 方法内是否调用 @DS 标注的类
```

### Step 2: 确认受影响卡片数量

```bash
# SLS 提取所有失败的 simIccid
grep -oP 'simIccid:\K[0-9]+' sls_output | sort -u > failed_cards.txt
wc -l failed_cards.txt
```

### Step 3: 时间窗口分析

```
SLS GetHistograms → 哪天开始出现? 是持续增长还是突发?
如果是突发 → 最近有代码变更(部署了 @Transactional 方法)
如果是持续 → @Transactional 方法一直存在但最近数据量增大触发
```

---

## Phase 3: DMS 验证 (半自动)

### Step 1: 查询 cancel 状态

```bash
aliyun dms-enterprise ExecuteScript \
  --Tid {TID} --DbId {DBID} --Logic false \
  --Script "SELECT sim_iccid, execute_result, created_at, updated_at
            FROM action_detail_cancel
            WHERE sim_iccid IN ({failed_iccids})
            AND created_at >= '{start_time}'
            ORDER BY created_at DESC" \
  --endpoint dms-enterprise.aliyuncs.com --profile dms
```

### Step 2: 扫描其他 action

```bash
for table in action_detail_suspend action_detail_resume action_detail_terminated action_detail_activate action_detail_change_bundle; do
  aliyun dms-enterprise ExecuteScript \
    --Tid {TID} --DbId {DBID} --Logic false \
    --Script "SELECT sim_iccid, execute_result, created_at FROM $table WHERE sim_iccid IN ({iccids}) AND created_at >= '{start}'" \
    --endpoint dms-enterprise.aliyuncs.com --profile dms
done
```

### 分类规则

```
if 某卡有 terminated 记录 → ⚠️ 已废弃, 不需重试
if 某卡有 activate 记录(在 cancel 之后) → ⚠️ 已重激活, 人工确认
if 某卡仅有 cancel 记录 → ✅ 可直接 retryCancelBundle
```

---

## Phase 4: 代码修复 (自动)

### Fix 1: 移除 @Transactional

```java
// CancelBundleService.java
- @Transactional(rollbackFor = Exception.class)
  public AjaxResult cancelBundle(...) { ... }

// SimApiSupportServiceImpl.java  
- @Transactional(rollbackFor = Exception.class)
  public AjaxResult cancel(...) { ... }
```

### Fix 2: 新增补偿接口 (TestController)

```java
@PostMapping("/retryCancelBundle")
public AjaxResult retryCancelBundle(@RequestBody List<String> simIccidList) {
    List<String> failedList = new ArrayList<>();
    List<String> successList = new ArrayList<>();
    for (String simIccid : simIccidList) {
        try {
            AjaxResult result = cancelBundleService.cancelBundle(simIccid, null, null, false);
            if (result != null && result.isSuccess()) {
                successList.add(simIccid);
            } else {
                failedList.add(simIccid);
            }
        } catch (Exception e) {
            failedList.add(simIccid);
        }
    }
    // return {total, success, failed, successList, failedList}
}
```

### 分支策略

```
hotfix/{issue-id}-{service} → merger to master-new
tag: hotfix-sphereII-v{X}.{Y}.{Z}-alpha.{N}-{date}{seq}
```

---

## Phase 5: 部署 + 监控 (手动)

### Step 1: 确认新镜像启动

```
SLS: "Started ContractApplication" AND pod_name != old_pod_name
→ 确认 30s 内无 "Application run failed"
```

### Step 2: 单张测试

```bash
curl -X POST 'http://{host}/retryCancelBundle' \
  -H 'Content-Type: application/json' \
  -d '["{one_failed_iccId}"]'
```

### Step 3: 监控结果

```
SLS: "retryCancelBundle simIccid"
SLS: "cancel error"
→ 确认: retry 日志 > 0 AND cancel error == 0
```

### Step 4: 全量重试

```bash
curl -X POST 'http://{host}/retryCancelBundle' \
  -H 'Content-Type: application/json' \
  -d '{full_json_array_of_safe_cards}'
```

### Step 5: 事后验证

```
DMS: SELECT ... FROM action_detail_cancel WHERE sim_iccid IN (...)
SLS: retryCancelBundle count == total safe cards
```

---

## Phase 6: Jira 回填 (自动)

### 必须包含
1. 🔬 根因 + 调用链
2. 📊 SLS 数据 (失败卡片数/时间窗口)
3. 📊 DMS 数据 (各表命中/分类/重试可行性)
4. ✅ 代码修复 (diff + 文件清单)
5. 🔧 curl 命令 (单张+全量)
6. 📈 验证结果 (SLS retry count + DMS reconfirm)

### 附件
- PR-{id}-plan.md (创建时)
- PR-{id}-{service}-report.md (回填时)
- contract-service-cancel-dms-analysis.md (DMS分析)
- contract-service-cancel-failed-cards-retry.md (失败卡片列表)

---

## 检查清单 (Level 3 — 5轮裁决)

```
[ ] SLS 确认错误特征: "Table doesn't exist" + @DS 标注
[ ] 确认受影响卡片数量+时间窗口
[ ] grep 源码确认 @Transactional+@DS 冲突点
[ ] DMS 验证 action_detail_cancel 状态
[ ] DMS 扫描其他 action 表 (suspend/resume/terminated/activate)
[ ] 分类卡片: 安全重试 / 需人工确认 / 已废弃
[ ] 代码修复: 移除 @Transactional + 新增补偿接口
[ ] commit + push + merge master-new
[ ] 打 tag (自动递增)
[ ] 部署后 SLS 确认新 Pod 正常启动
[ ] 单张测试 retryCancelBundle
[ ] 全量重试
[ ] SLS 监控确认 0 cancel error
[ ] DMS 再次确认
[ ] Jira 回填 (8段报告 + 附件)
```

---

## 案例参考

| 案例 | Jira | 服务 | 影响 | 结果 |
|------|------|------|------|:--:|
| 2026-05-16 | PR-6672 | contract-service | 55张卡 | ✅ 100%恢复 |
