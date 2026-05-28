---
service: sim-service
group: cube/platform
repo: https://git.io.linksfield.net/cube/platform/sim-service
branch: master
analyzed_at: 2026-05-28
completeness: full
---

# sim-service — SIM 卡全生命周期管理服务

## 1. 基本信息

| 项目 | 值 |
|------|-----|
| 仓库 | https://git.io.linksfield.net/cube/platform/sim-service |
| Java 版本 | 11 |
| 构建工具 | Maven |
| 包路径 | `net.linksfield.sim` |
| 入口类 | `SimApplication.java` |
| MyBatis Mapper 扫描 | `net.linksfield.sim.dao` |
| Feign 客户端扫描 | `@EnableFeignClients` (自动扫描) |

## 2. 技术栈

| 分类 | 技术 | 版本 | 用途 |
|------|------|:--:|------|
| 框架 | Spring Boot | 2.x | 应用框架 |
| 微服务 | Spring Cloud Bootstrap | — | 配置中心 (Apollo) |
| 多数据源 | dynamic-datasource | 3.4.1 | `@DS` 注解切换数据源 |
| ORM | MyBatis-Plus | — | 数据库操作 |
| 分页 | PageHelper | 1.4.1 | 分页查询 |
| 连接池 | HikariCP | 5.0.1 | 数据库连接池 |
| 缓存 | Redis (Jedis) | 3.7.0 | 缓存 + 分布式锁 |
| 分布式锁 | Redisson | — | 高级分布式锁 |
| 消息队列 | RocketMQ (ons-client) | 1.8.8.8 | 异步消息 |
| 事件中心 | EventCenter | — | 生产者/消费者 |
| 搜索引擎 | Elasticsearch | — | SIM 卡搜索 |
| 文件存储 | Aliyun OSS | 3.16.2 | 文件/Excel 存储 |
| Excel | EasyExcel | 3.1.1 | Excel 读写 |
| PDF | iText (html2pdf) | 4.0.3 | PDF 生成 |
| 模板 | Thymeleaf | — | HTML 模板渲染 |
| 日志 | Aliyun SLS | 0.6.75 | 日志采集+生产 |
| 服务调用 | OpenFeign + Ribbon | — | 微服务间调用 |
| 业务支持 | BusinessSupport | — | sphere2 公共组件 |
| 审计日志 | AuditLog | — | 操作审计 |
| 鉴权 | AuthorizeSupport | — | 权限控制 |
| 重试 | Spring Retry | — | 失败重试 |

## 3. 启动注解分析

```java
@SpringBootApplication
@EnableFeignClients                                          // Feign 服务调用
@MapperScan("net.linksfield.sim.dao")                        // MyBatis Mapper 扫描
@EnableEventCenterProducer(name = "sim")                     // 事件生产者 (sim)
@EnableEventCenterConsumer(name = "sim", value = {"leo"},    // 事件消费者 (leo 事件)
    consumerTokenUrl = "http://svc-sim")
@EnableBusinessSupport                                       // sphere2 业务支撑
@EnableAuditLog                                              // 操作审计
@EnableRetry                                                 // 重试机制
@EnableAuthorizeSupport(autoReport = true,                   // 权限控制 (sphere 租户)
    defaultModule = "sim-service",
    defaultTenant = PermissionConstants.Tenant.SPHERE)
```

关键依赖链: `EventCenter` 生产消费、`AuthorizeSupport` 鉴权、`AuditLog` 审计

注解全局效果:
- `@AjaxResultWrapper` — 大部分 Controller 响应自动包装为标准 JSON
- `@EnableAuthorizeSupport` — 接口级权限控制
- `@EnableAuditLog` — 自动记录操作审计日志
- `@EnableRetry` — 失败自动重试
- `@EnableBusinessSupport` — Sphere2 平台公共组件支持
- `@EnableEventCenterProducer(name="sim")` — 事件生产者
- `@EnableEventCenterConsumer(name="sim", value={"leo"})` — 事件消费者

## 4. 配置文件

| 文件 | 说明 |
|------|------|
| `sim/pom.xml` | Maven 依赖配置 |
| `sim/src/main/resources/application*.yml` | Spring 配置 (多个环境) |
| `sim/src/main/resources/db/migration/` | Flyway 数据库迁移脚本 |
| `sim/src/main/resources/i18n/` | 国际化资源文件 |
| `sim/src/main/resources/templates/` | Thymeleaf 模板 |

---

## 5. API 端点清单（完整）

### 5.1 SimListController — `/sim/list` (18 个端点 — SIM 卡列表)

| 方法 | 路径 | 功能 | 控制器方法 | 权限 | 审计 |
|:--:|------|------|------|:--:|:--:|
| POST | `/sim/list` | 查询 SIM 卡列表（分页+多条件筛选） | `querySimList` | `sphere-sim-simList:read` | ✅ |
| GET | `/sim/list/top` | SIM 卡置顶列表（按 ICCID 批量查） | `querySimListTop` | `sphere-sim-simList:read` | — |
| POST | `/sim/list/export/all` | 导出全部 SIM 列表（按查询条件） | `exportSimList` | `sphere-sim-simList:read` | ✅ |
| POST | `/sim/list/export` | 按选中 ICCID 列表导出 | `exportSimByIccid` | `sphere-sim-simList:read` | ✅ |
| GET | `/sim/list/batch_query/template/download/{type}` | 下载批量查询模板（xlsx/csv） | `downloadBatchQueryTemplate` | `sphere-sim-simList:read` | — |
| POST | `/sim/list/batch_query/file/parse` | 解析 ICCID 批量查询上传文件 | `parseBatchQueryFile` | `sphere-sim-simList:read` | — |
| POST | `/sim/list/cube` | SIM 列表（适配 cube 平台，临时） | `queryCubeSimList` | — | — |
| POST | `/sim/list/cube/export` | 导出 SIM 列表到任务中心（cube） | `exportCubeSimList` | — | — |
| PUT | `/sim/list/device_name` | 修改设备名称 | `updateSimDeviceName` | — | — |
| GET | `/sim/list/tag/org` | 查询运营客户下的标签列表 | `queryTagByOrgCode` | — | — |
| PUT | `/sim/list/notes` | 修改 SIM 卡备注 | `updateSimNotes` | — | — |
| PUT | `/sim/list/tag` | 保存/添加 SIM 卡标签 | `addSimTag` | — | — |
| PUT | `/sim/list/batch_update/check/{org}` | 校验批量更新文件 | `checkBatchUpdate` | — | — |
| PUT | `/sim/list/batch_update/{org}` | 批量更新（文件上传方式） | `batchUpdate` | — | — |
| PUT | `/sim/list/batch_update/imei` | 批量更新 IMEI | `batchUpdateImei` | — | — |
| PUT | `/sim/list/batch_update/apn` | 批量更新 APN | `batchUpdateApn` | — | — |
| GET | `/sim/list/org` | 根据 SIM ICCID 查询企业编码 | `queryOrgBySimIccid` | — | — |
| POST | `/sim/list/org` | 根据 SIM ICCID 查询企业编码（POST 方式） | `queryOrgBySimIccidByPost` | — | — |

**统计**: 共 18 个端点。其中权限控制 7 个，审计日志 3 个，cube 兼容接口 2 个。

---

### 5.2 SimDetailController — `/sim/detail` (30 个端点 — SIM 卡详情)

| 方法 | 路径 | 功能 | 控制器方法 | 权限 | 审计 |
|:--:|------|------|------|:--:|:--:|
| GET | `/sim/detail/query/cross_system` | 跨系统查询 SIM 卡信息 | `crossSystemQuerySim` | `sphere-sim-simList:read` (匿名) | — |
| GET | `/sim/detail/basic/{sim_iccid}` | 查询 SIM 基本详情 | `querySimBasic` | `simList+finance:read` | ✅ |
| GET | `/sim/detail/spec/{sim_code}` | 导出 SIM 卡规格信息 | `exportSimSpec` | `simList+finance:read` | ✅ |
| GET | `/sim/detail/network/{sim_iccid}/{org_code}` | 查询 SIM 子网络信息 | `querySimChildNetwork` | `simList+finance:read` | — |
| GET | `/sim/detail/child/basic/{sim_iccid}` | 查询子 SIM 卡基本信息 | `querySimChildBasic` | `sphere-sim-simList:read` | — |
| GET | `/sim/detail/cell` | 查询小区信息 | `queryCellInfo` | `sphere-sim-simList:read` | — |
| GET | `/sim/detail/diagnosis/{sim_iccid}` | SIM 卡诊断 | `querySimDiagnosis` | `sphere-sim-simList:read` | — |
| GET | `/sim/detail/contract/{sim_iccid}` | 查询 SIM 子合同 | `querySimChildContract` | `sphere-sim-simList:read` | ✅ |
| GET | `/sim/detail/coverage/{coverage_id}` | 查询覆盖区域结果列表 | `queryCoverageResList` | `sphere-sim-simList:read` | ✅ |
| GET | `/sim/detail/coverage/export/{coverage_id}` | 导出覆盖区域结果 | `exportCoverage` | `sphere-sim-simList:read` | — |
| GET | `/sim/detail/overuse_policy/{bundle_code}` | 根据套餐码查询超量策略 | `queryOverStrategyByCode` | `sphere-sim-simList:read` | — |
| GET | `/sim/detail/bundle/history/{sim_iccid}` | 查询 SIM 套餐历史列表 | `queryBundleHistoryList` | `sphere-sim-simList:read` | ✅ |
| GET | `/sim/detail/status/trajectory/{sim_iccid}` | 查询 SIM 状态轨迹 | `querySimStatusTrajectory` | `simList+finance:read` | ✅ |
| GET | `/sim/detail/status/trajectory/export/{sim_iccid}` | 导出 SIM 状态轨迹 | `exportSimStatusTrajectory` | `simList+finance:read` | — |
| GET | `/sim/detail/cdr/list/{sim_iccid}` | 查询 SIM CDR 话单列表 | `querySimCdrList` | `simList+finance:read` | — |
| GET | `/sim/detail/bundle/list/{sim_iccid}/{status}` | 查询 SIM 套餐列表（按状态） | `querySimBundleList` | `simList+finance:read` | — |
| GET | `/sim/detail/bundle/list/{sim_iccid}/{so}/{bc}` | 查询 SIM 套餐详情（按 SO+BC） | `querySimBundleDetail` | `sphere-sim-simList:read` | — |
| GET | `/sim/detail/bundle/cycle/list/{sim_iccid}/{p}/{s}` | 查询 SIM 套餐周期列表 | `querySimBundleCycleList` | `sphere-sim-simList:read` | — |
| GET | `/sim/detail/usage/list/{usage_type}/{time_type}/{sim_iccid}` | 查询 SIM 用量（按用量类型+时间类型） | `querySimUsage` | `simList+finance:read` | — |
| GET | `/sim/detail/event/list/{sim_iccid}` | 查询 SIM 事件列表 | `querySimEventList` | `simList+finance:read` | — (含 `@SphereResponseEmbellish`) |
| GET | `/sim/detail/contract/detail/{sim_iccid}` | 查询 SIM 合同详情 | `querySimContractDetail` | `simList+finance:read` | ✅ |
| GET | `/sim/detail/sku/service/{sim_iccid}` | 查询 SIM 服务 SKU 详情 | `querySimServiceSkuDetail` | `simList+finance:read` | — |
| GET | `/sim/detail/production/{sim_iccid}` | 查询 SIM 生产详情 | `querySimProductionDetail` | `simList+finance:read` | — |
| GET | `/sim/detail/inventory/{sim_iccid}` | 查询 SIM 库存详情 | `querySimInventoryDetail` | `simList+finance:read` | — |
| GET | `/sim/detail/tag` | 根据企业编码和 SIM ICCID 查询标签 | `queryTagByOrgAndSimIccid` | — | — |
| GET | `/sim/detail/status/cube/trajectory/export/{sim_iccid}` | 导出 SIM 状态轨迹到 Cube | `exportSimStatusTrajectoryToCube` | `sphere-sim-simList:read` | — |
| GET | `/sim/detail/service/contract/list/{sim_iccid}/{status}` | 查询 SIM 服务合同列表 | `querySimServiceContractList` | `simList+finance:read` | — |
| GET | `/sim/detail/belong/{sim_iccid}` | 根据 ICCID 查询归属企业编码 | `queryOrgCodeByIccid` | — | — |
| GET | `/sim/detail/event/sync` | 同步 SIM 事件 | `syncSimEvent` | — | — |
| POST | `/sim/detail/connection/status` | 连接状态查询（cube） | `connectionStatus` | — | — |

**统计**: 共 30 个端点。其中权限控制 27 个，审计日志 7 个，无需权限 3 个。

---

### 5.3 SimApiController — `/sim/api` (24 个端点 — SIM 开放 API)

| 方法 | 路径 | 功能 | 控制器方法 | bizType | 审计 |
|:--:|------|------|------|------|:--:|
| GET | `/sim/api/sim_change_list_task` | 手动触发定时任务：每月汇总 SIM 卡变更记录 | `querySimChangeList` (task) | — | — |
| GET | `/sim/api/sim_change_list` | 查询 SIM 变更记录（start_id/sim_iccids/page_size） | `querySimChangeList` | — | — |
| GET | `/sim/api/sim/query` | 查询 MNO SIM 信息（page_no/sim_ids/org_id/shipped_after/shipped_before） | `queryMnoSimInfo` | — | — |
| GET | `/sim/api/sim/query_max_page_no` | 查询 MNO SIM 信息最大页码（org_id） | `queryMnoSimInfoMaxPageNo` | — | — |
| GET | `/sim/api/sim/daddy_task` | 手动刷新每日 SIM 卡统计汇总数据 | `startTask` | — | — |
| GET | `/sim/api/{sim_iccid}` | 查询 SIM 详情 | `querySimDetail` | — | — |
| GET | `/sim/api/list` | 查询 SIM 列表（org_code/key_id/status/page_no/page_size/order_id/sim_ids） | `querySimList` | — | — |
| GET | `/sim/api/{sim_iccid}/bundle/list` | 查询 SIM 套餐列表（status/page_no/page_size） | `querySimBundleList` | — | — |
| GET | `/sim/api/status` | 查询 SIM API 状态（sim_id/element） | `queryApiSimStatus` | — | — |
| POST | `/sim/api/valid/sims` | 企业网关校验 SIM 参数 | `validSimParam` | — | — |
| POST | `/sim/api/valid/sims/orgs` | 企业网关校验 SIM 参数（orgs 版本） | `validSims` | — | — |
| POST | `/sim/api/async_result_query` | 异步结果查询 | `asyncResultQuery` | — | — |
| POST | `/sim/api/resume` | 复机 | `resume` | RESUME | — |
| POST | `/sim/api/suspend` | 暂停 | `suspend` | SUSPEND | — |
| POST | `/sim/api/activate` | 激活 | `activate` | ACTIVE | — |
| POST | `/sim/api/transfer` | 转移 | `transfer` | TRANSFER | — |
| POST | `/sim/api/reset` | 重置 | `reset` | RESET | — |
| POST | `/sim/api/restore` | 恢复 | `restore` | RESTORE | — |
| POST | `/sim/api/cancel` | 取消订单 | `cancel` | CANCEL_ORDER | — |
| GET | `/sim/api/{sim_iccid}/bundle/can_use` | 查询可绑定套餐列表 | `queryApiSimCanUseBundleList` | — | — |
| GET | `/sim/api/remaining_data/{sim_id}` | 查询 SIM 实时剩余用量 | `querySimRemainingData` | — | — |
| POST | `/sim/api/select_and_lock` | 锁定本地网络 | `selectAndLockLocalNetwork` | SELECTED_LOCAL_OPERATORS | — |
| POST | `/sim/api/usage/A1` | 查询 SIM A1 流量用量 | `querySimA1Usage` | — | — |
| GET | `/sim/api/bundle/coverage_spec` | 查询套餐覆盖地规格 | `queryBundleCoverageSpec` | — | — |
| POST | `/sim/api/bundle_ordering` | 订购套餐 | `bundleOrdering` | CREATE_ORDER | — |
| POST | `/sim/api/bundle_ordering/batch` | 批量订购套餐 | `batchBundleOrdering` | — | — |
| POST | `/sim/api/bundle_ordering/batch/invoke` | 批量订购结果回调 | `invokeBatchBundleOrdering` | — | — |
| POST | `/sim/api/replace_bundle` | 更换套餐 | `replaceBundle` | REPLACE_BUNDLE | — |
| PUT | `/sim/api/reinitialize` | 恢复卡片出厂设置 | `reinitializeSim` | REINITIALIZE | — |
| GET | `/sim/api/skip_execute_bundle` | 判断卡片是否允许跳过正在执行的套餐 | `skipExecuteBundle` | — | — |

**核心业务操作 bizType 映射**:

| bizType | 操作 | 说明 |
|------|------|------|
| RESUME | 复机 | 恢复暂停的 SIM 卡 |
| SUSPEND | 暂停 | 暂停 SIM 卡服务 |
| ACTIVE | 激活 | 激活 SIM 卡 |
| TRANSFER | 转移 | 转移 SIM 卡归属 |
| RESET | 重置 | 重置 SIM 卡状态 |
| RESTORE | 恢复 | 恢复 SIM 卡 |
| CANCEL_ORDER | 取消订单 | 取消 SIM 卡订单 |
| CREATE_ORDER | 订购套餐 | 为 SIM 卡订购套餐 |
| REPLACE_BUNDLE | 更换套餐 | 更换已有套餐 |
| REINITIALIZE | 恢复出厂设置 | 恢复卡片出厂设置 |
| SELECTED_LOCAL_OPERATORS | 锁定本地网络 | 选择并锁定本地运营商 |

---

### 5.4 SimCommonController — `/sim/common` (2 个端点 — 公共接口)

| 方法 | 路径 | 功能 | 控制器方法 | 权限 | 审计 |
|:--:|------|------|------|:--:|:--:|
| GET | `/sim/common/mcc/list` | 国家/地区下拉列表 | `queryCountryAreaDownList` | `sphere-sim-simList:read` | — |
| GET | `/sim/common/mno/list` | 运营商下拉列表 | `queryMnoDownList` | `sphere-sim-simList:read` | — |

---

### 5.5 SimServiceController — `/sim/service` (3 个端点 — SIM 服务管理)

| 方法 | 路径 | 功能 | 控制器方法 | 权限 | 审计 |
|:--:|------|------|------|:--:|:--:|
| POST | `/sim/service/list` | 查询 SIM 服务列表 | `querySimServiceList` | `sphere-sim-simList:read` | ✅ |
| POST | `/sim/service/list/export` | 导出 SIM 服务列表 | `exportSimServiceList` | `sphere-sim-simList:read` | ✅ |
| POST | `/sim/service/list/cube/export` | 导出 SIM 服务列表到 Cube | `getSimServiceExportFile` | — | — |

---

### 5.6 SimSmsController — `/sim/sms` (4 个端点 — SIM 短信)

| 方法 | 路径 | 功能 | 控制器方法 | 权限 | 审计 |
|:--:|------|------|------|:--:|:--:|
| GET | `/sim/sms/list` | 查询短信发送列表（sim_iccid/customer_code/page_no/page_size） | `queryCountryAreaDownList` | `sphere-sim-simList:read` | — |
| POST | `/sim/sms/send` | 发送短信 | `send` | `sphere-sim-send-sms:write` | — |
| POST | `/sim/sms/config/org_code/enable` | 启用企业短信自动报告配置 | `sphere2SmsAutoReportConfig` | `sphere-customer:sms-write` | — |
| GET | `/sim/sms/has_sms_config/{org_code}` | 检查企业是否有短信配置 | `hasSmsConfig` | `sphere-customer:read` | — |

---

### 5.7 OperationManagementController — `/mno_gateway` (15 个端点 — MNO Gateway 中转操作管理)

| 方法 | 路径 | 功能 | 控制器方法 | 权限 | 审计 |
|:--:|------|------|------|:--:|:--:|
| GET | `/mno_gateway/mnos/names` | 列出 MNO 名称 | `listMno` | `sphere-mno-data:read` | — |
| GET | `/mno_gateway/customers/names` | 列出客户名称 | `listCustomerByName` | `sphere-mno-data:read` | — |
| GET | `/mno_gateway/operations` | 列出 MNO 网关操作记录 | `listMnoGatewayOperation` | `sphere-mno-data:read` | — |
| GET | `/mno_gateway/operations/{id}/sub-operations` | 列出 MNO 网关子操作（按操作 ID） | `listMnoGatewaySubOperationById` | `sphere-mno-data:read` | — |
| GET | `/mno_gateway/operations/{id}/detail` | 获取 MNO 网关操作详情 | `getMnoGatewayOperationDetail` | `sphere-mno-data:read` | — |
| GET | `/mno_gateway/operations/{id}/mno-operations` | 列出 MNO 操作（按操作 ID） | `listMnoOperationById` | `sphere-mno-data:read` | — |
| PUT | `/mno_gateway/operations/exceptions/dispose/ids` | 按 ID 批量处理异常 | `disposeExceptionByIds` | `sphere-mno-data:read` | — |
| GET | `/mno_gateway/operations/exceptions/dispose/validate` | 异常处置校验（10 参数） | `validateForExceptionDispose` | `mnogateway-operation:operation-write` | — |
| GET | `/mno_gateway/operations/exceptions/dispose/mnos/names` | 获取异常处置 MNO 名称列表 | `listMnoNameForExceptionDispose` | `sphere-mno-data:read` | — |
| PUT | `/mno_gateway/operations/exceptions/dispose` | 处置异常（10 参数） | `disposeException` | `mnogateway-operation:operation-write` | — |
| PUT | `/mno_gateway/operations/retry/ids` | 按 ID 批量重试 | `retryByIds` | `mnogateway-produce:retry` | — |
| GET | `/mno_gateway/operations/retry/validate` | 重试校验（10 参数） | `validateForRetry` | `mnogateway-produce:retry` | — |
| PUT | `/mno_gateway/operations/retry` | 重试操作（10 参数） | `retry` | `mnogateway-produce:retry` | — |
| POST | `/mno_gateway/add/initiator` | 添加操作发起人 | `addInitiator` | `mnogateway-operation:operation-write` | — |
| GET | `/mno_gateway/initiators` | 列出操作发起人列表 | `ListInitiator` | `sphere-mno-data:read` | — |

**MNO Gateway 权限清单**:

| 权限 | 用途 |
|------|------|
| `sphere-mno-data:read` | MNO 数据查询 |
| `mnogateway-operation:operation-write` | MNO 网关操作异常处置/发起人管理 |
| `mnogateway-produce:retry` | MNO 网关操作重试 |

---

### 5.8 端点总览统计

| Controller | 端点数 | 路径前缀 | 有权限控制 | 有审计日志 |
|------|:--:|------|:--:|:--:|
| SimListController | 18 | `/sim/list` | 7 | 3 |
| SimDetailController | 30 | `/sim/detail` | 27 | 7 |
| SimApiController | 24 | `/sim/api` | — | — |
| SimCommonController | 2 | `/sim/common` | 2 | 0 |
| SimServiceController | 3 | `/sim/service` | 2 | 2 |
| SimSmsController | 4 | `/sim/sms` | 4 | 0 |
| OperationManagementController | 15 | `/mno_gateway` | 15 | 0 |
| **合计** | **96** | — | **57** | **12** |

**权限体系**:

| 权限 | 适用接口 |
|------|------|
| `sphere-sim-simList:read` | SIM 列表查询、详情查看 |
| `simList+finance:read` | SIM 详情 + 财务数据 |
| `sphere-sim-send-sms:write` | 发送短信 |
| `sphere-customer:sms-write` | 企业短信自动报告配置 |
| `sphere-customer:read` | 企业短信配置查询 |
| `sphere-mno-data:read` | MNO 网关数据查询 |
| `mnogateway-operation:operation-write` | MNO 网关操作写入 |
| `mnogateway-produce:retry` | MNO 网关重试 |

---

## 6. 定时任务 (Scheduled Tasks, 4 个)

| 序号 | 任务类 | 功能说明 | 触发方式 |
|:--:|------|------|------|
| 1 | `CreateSimCardChangeLogScheduled` | 每月汇总 SIM 卡变更记录 | 手动触发: `GET /sim/api/sim_change_list_task` |
| 2 | `EsSimUpdateTask` | ES 同步更新任务（同步 SIM 卡数据到 Elasticsearch） | 定时自动 |
| 3 | `ReportWeeklySimActivationScheduled` | 每周 SIM 激活汇总报告 | 定时自动 |
| 4 | `SimStatisticsScheduled` | SIM 卡统计数据定时任务 | 手动触发: `GET /sim/api/sim/daddy_task` |

---

## 7. Feign Clients (下游服务调用, 22 个)

| Feign Client | 调用目标服务 | 说明 |
|------|------|------|
| `ApiBbcSupportFeign` | BBC API 支持服务 | BBC 业务 API 支撑 |
| `ApiSupportFeign` | API 支持服务 | 通用 API 支撑 |
| `AquariusFeign` | Aquarius 服务 (Sphere2) | Sphere2 平台 Aquarius |
| `BaseDataFeign` | 基础数据服务 | 基础数据查询 |
| `BusinessSupportFeign` | 业务支撑服务 (Sphere2) | Sphere2 业务支撑 |
| `CdrAggregatingFeign` | CDR 聚合服务 | CDR 话单聚合 |
| `CdrPersistenceFeign` | CDR 持久化服务 | CDR 话单持久化 |
| `ContractFeign` | contract-service (合同服务) | 合同数据查询 |
| `ContractImsiFeign` | 合同 IMSI 服务 | IMSI 合同关联 |
| `CubeServerFeign` | Cube Server | Cube 平台服务 |
| `DataPoolFeign` | 数据池服务 | 数据池查询 |
| `DataPoolSphere2Feign` | Sphere2 数据池 | Sphere2 数据池 |
| `IOTContractFeign` | IoT 合同服务 | IoT 合同数据 |
| `LeoCustomerFeign` | Leo 客户服务 | Leo 客户数据 |
| `LeoScmFeign` | Leo 供应链服务 | Leo 供应链 |
| `LeoSupplyFeign` | Leo 供应服务 | Leo 供应数据 |
| `LeoWmsFeign` | Leo 仓库服务 | Leo WMS 仓库 |
| `MestabaseFeign` | Metabase 分析服务 | Metabase 数据分析 |
| `MnogatewayDispatcherFeign` | MNO 网关调度服务 | MNO 网关调度 |
| `OpenPlatformFeignClient` | 开放平台 | 开放平台 API |
| `RuleEngineFeign` | 规则引擎 | 通用规则引擎 |
| `Sphere2CustomerFeignClient` | Sphere2 客户服务 | Sphere2 客户数据 |
| `VirgoFeign` | Virgo 服务 | Virgo 服务 |
| `RuleEngineSphere2Feign` | Sphere2 规则引擎 | Sphere2 专用规则引擎 |
| `RuleEngineSphere2FormDataFeign` | Sphere2 规则引擎 FormData | Sphere2 规则引擎表单数据 |

每个 Feign Client 对应 `feign/service/` 和 `feign/service/impl/` 下的 Service/Impl 类。

---

## 8. 核心业务服务 (Key Services)

| 服务 | 说明 |
|------|------|
| `SimListService` | SIM 卡列表查询、导出、批量操作 |
| `SimDetailService` | SIM 卡详情查询（基础信息、状态轨迹、CDR、套餐、用量等） |
| `SimApiService` | SIM 开放 API（复机、暂停、激活、转移、重置、恢复、订单管理） |
| `SimCommonService` | SIM 公共查询（国家/运营商下拉） |
| `SimServiceService` | SIM 服务管理（列表查询、导出） |
| `SimSmsService` | SIM 短信服务（列表、发送、配置管理） |
| `SimCardChangeLogInfoService` | SIM 卡变更记录管理 |
| `SimAsyncApiHandler` | SIM 异步 API 处理（处理异步操作结果） |
| `ApiAuthorizeManager` | API 授权管理 |

---

## 9. 数据层

### 9.1 Redis 配置 (多实例, 4 + 1)

| 配置类 | Redis 实例 | 用途 |
|------|------|------|
| `RedisConfig` | 主 Redis | 通用缓存 |
| `CubeRedisConfig` | Cube Redis | Cube 平台数据缓存 |
| `ElasticsearchRedisConfig` | ES Redis | ES 同步状态缓存 |
| `GatewayRedisConfig` | Gateway Redis | 网关数据缓存 |
| `RedissonConnectionConfiguration` | Redisson | 分布式锁 |

### 9.2 Redis 工具类

| 工具类 | 用途 |
|------|------|
| `RedisDistributedLock` | 分布式锁（基于 Redis） |
| `EsCacheUtil` | ES 缓存操作（Spring Data Redis） |
| `CommonRedisUtil` | Redis 通用操作 |
| `GatewayRedisUtil` | 网关 Redis 操作 |

### 9.3 Elasticsearch

| 组件 | 类 |
|------|-----|
| ES 配置 | `EsConfig.java` |
| ES 注解 | `@EsFieldNull`, `@EsHandle`, `@EsRetry` |
| ES AOP | `EsRequestAspect.java` |
| ES 查询构建 | `EsQueryListBuilder.java` |
| ES 常量 | `EsConstant.java` |

### 9.4 MyBatis-Plus / Mapper

| 组件 | 类 |
|------|-----|
| 配置 | `MybatisPlusConfig.java` |
| 自定义 Handler | `ServiceResourceListHandler`, `SowChargingItemHandler`, `SubconResourceListHandler` |
| DAO 层 | `sim/dao/` 目录 |
| XML Mapper | `sim/dao/xml/` 目录 |
| 数据库迁移 | `db/migration/` (Flyway) |

### 9.5 多数据源

使用 `dynamic-datasource` 3.4.1 实现 `@DS` 注解动态切换数据源，支持多个 MySQL 实例。

---

## 10. 消息队列 (RocketMQ)

| 组件 | 类 | 说明 |
|------|-----|------|
| 客户端配置 | `RocketMqClientConfig.java` | RocketMQ 客户端连接配置 |
| 生产者配置 | `RocketMqProducerConfig.java` | 消息生产者配置 |
| 配置属性 | `RocketmqProperties.java` | MQ 参数属性 |
| 消费者 | `listener/` 目录 | MQ 消费监听器（消费 leo 事件） |
| 业务处理 | `service/mq/` 目录 | MQ 消息业务逻辑处理 |

EventCenter 配置:
- Producer: `name=sim`
- Consumer: `name=sim`, 订阅 `leo` 事件
- Consumer Token URL: `http://svc-sim`

---

## 11. 数据实体 (Domain)

### 11.1 Entity

| 目录 | 说明 |
|------|------|
| `domain/entity/` | 数据库实体 (MyBatis-Plus Entity) |
| `domain/bo/contract/` | 合同业务对象 |
| `domain/bo/excel/` | Excel 业务对象 |
| `domain/dto/req/api/` | API 请求 DTO |
| `domain/dto/req/bbc/` | BBC 请求 DTO |
| `domain/dto/req/sharedpool/` | 共享池请求 DTO |
| `domain/dto/res/api/` | API 响应 DTO |
| `domain/dto/res/asset/` | 资产响应 DTO |
| `domain/dto/res/bbc/` | BBC 响应 DTO |
| `domain/dto/res/contract/` | 合同响应 DTO |
| `domain/dto/res/customer/` | 客户响应 DTO |
| `domain/dto/res/report/` | 报告响应 DTO |
| `domain/dto/res/sharedpool/` | 共享池响应 DTO |
| `domain/vo/req/service/` | 服务请求 VO |
| `domain/vo/req/sim/api/` | SIM API 请求 VO |
| `domain/vo/res/contract/` | 合同响应 VO |
| `domain/vo/res/detail/strategy/` | 详情策略 VO |
| `domain/vo/res/detail/usage/` | 用量详情 VO |
| `domain/vo/res/service/` | 服务响应 VO |
| `domain/vo/res/sim/api/` | SIM API 响应 VO |
| `domain/vo/res/sow/` | SOW 响应 VO |

### 11.2 子模块

| 子模块 | 说明 |
|------|------|
| `domain/autoflowsphere/` | 自动流 sphere 领域 |
| `domain/mnogateway/` | MNO 网关领域 |
| `domain/riskcontrol/` | 风控领域 |

---

## 12. 业务服务层 (Service 目录)

### 12.1 核心服务目录

| 服务目录 | 说明 |
|------|------|
| `service/api/` | API 模块服务 |
| `service/api/impl/` | API 实现 |
| `service/asset/` | 资产管理 |
| `service/autoflow/` | 自动流 |
| `service/autoflow/impl/` | 自动流实现 |
| `service/bbc/` | BBC 业务 |
| `service/convert/` | 数据转换 |
| `service/cube/` | Cube 适配层 |
| `service/datapool/` | 数据池 |
| `service/datapool/impl/` | 数据池实现 |
| `service/impl/` | 通用服务实现 |
| `service/mq/` | 消息队列处理 |
| `service/riskcontrol/` | 风控 |
| `service/riskcontrol/impl/` | 风控实现 |
| `service/es/` | Elasticsearch 服务 (来自 `net.linksfield.contract`) |

### 12.2 管理器 (Manager)

| Manager | 说明 |
|------|------|
| `manager/impl/` | 通用 Manager |
| `manager/impl/usage/` | 用量 Manager |

---

## 13. 常量与枚举

| 常量/枚举 | 说明 |
|------|------|
| `SimConstant.java` | SIM 常量 |
| `SimApiResult.java` | API 返回结果常量 |
| `EnterpriseApiResult.java` | 企业 API 结果 |
| `EsConstant.java` | ES 常量 |
| `OpsConstants.java` | 运营常量 |
| `PeriodUnit.java` | 周期单位 |
| `CustomerShareSkuConstant.java` | 客户共享 SKU |
| `SimStatusProcessingConstant.java` | SIM 状态处理 |
| `SoStatus.java` | SO 状态 |
| `SupplierConstant.java` | 供应商常量 |
| `ApiAuthorizeEnums.java` | API 鉴权枚举 |
| `ApiSyncResultEnum.java` | API 同步结果 |
| `LeoEnums.java` | Leo 枚举 |
| `ResultCodeEnum.java` | 结果码 |
| `SimApiEnum.java` | SIM API 枚举 |
| `SimApiExceptionEnum.java` | SIM API 异常 |
| `SimEnums.java` | SIM 通用枚举 |
| `SimEventEnums.java` | SIM 事件枚举 |
| `SimExceptionEnum.java` | SIM 异常 |
| `SimServiceEnums.java` | SIM 服务枚举 |
| `SimTaskCenterEnums.java` | SIM 任务中心 |
| `SlsIndexTypeEnum.java` | SLS 索引类型 |

---

## 14. 已知陷阱 (知识库匹配)

| ID | 陷阱 | 匹配特征 | 风险 |
|----|------|----------|:--:|
| K001 | Jackson 未知字段 | ServiceResourceListHandler 中处理 JSON | HIGH |
| K013 | Redis 锁泄漏 | EsCacheUtil 中的 get+delete 操作 | HIGH |
| K009 | parallelStream NPE | 如使用 ForkJoinTask | MEDIUM |
| K014 | 序列化不一致 | 多个 Redis 实例, 需统一序列化方式 | MEDIUM |
| SOP-001 | @Transactional + @DS 冲突 | 多数据源配置 | HIGH |

---

## 15. 依赖关系

### 15.1 上游调用者
- `api-gateway-cube` — 网关路由到 sim-service
- `api-gateway-sphere-2` — Sphere2 网关
- `cube-new` (前端) — 通过网关调用

### 15.2 下游依赖 (通过 Feign)
- aquarius — Aquarius 服务
- base-data — 基础数据服务
- business-support — 业务支撑服务
- cdr-aggregating — CDR 聚合服务
- cdr-persistence — CDR 持久化服务
- contract-service — 合同服务
- cube-server — Cube 平台
- data-pool — 数据池
- iot-contract — IoT 合同服务
- leo-customer — Leo 客户服务
- leo-scm — Leo 供应链
- leo-supply — Leo 供应
- leo-wms — Leo 仓库
- mestabase — Metabase 分析
- mno-gateway-dispatcher — MNO 网关调度
- open-platform — 开放平台
- rule-engine — 规则引擎
- sphere2-customer — Sphere2 客户服务
- virgo — Virgo 服务

### 15.3 基础设施依赖
- MySQL (多数据源, dynamic-datasource)
- Redis × 4 (主/Cube/ES/Gateway) + Redisson
- Elasticsearch
- RocketMQ (ons-client)
- Aliyun OSS
- Aliyun SLS
- Apollo 配置中心
- Flyway (数据库迁移)
