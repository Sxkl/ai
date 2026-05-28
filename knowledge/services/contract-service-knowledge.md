# contract-service — 服务知识与故障案例库

> **版本**: v1.0 | **日期**: 2026-05-16 | **仓库**: cube/platform/contract-service  
> **SLS**: uwp-prod/k8s-newk8s-contract (cn-hongkong) | **DMS**: sphere2-contract (DbId: 57508735)

---

## 一、服务架构

### 1.1 多数据源拓扑

```
┌─────────────────────────────────────────────────────────┐
│                   contract-service                       │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │   master     │  │   sim_db     │  │  billing_db   │ │
│  │ (默认数据源)  │  │  @DS("sim_db") │  │@DS("billing")│ │
│  │ sphere2-     │  │              │  │               │ │
│  │ contract     │  │  sim库        │  │  billing库     │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘ │
│         │                 │                  │          │
│  ┌──────▼───────┐  ┌──────▼───────┐          │          │
│  │30+ ServiceImpl│  │ SimMapper    │          │          │
│  │(默认)         │  │ SimServiceImpl│         │          │
│  │              │  │ SimEventMapper│         │          │
│  └──────────────┘  └──────────────┘          │          │
│                                               │          │
│  ┌───────────────────────────────────────────┐│          │
│  │           Redis (3个连接工厂)               ││          │
│  │  RedisConfig │ ExpireEventRedisConfig      ││          │
│  │  ElasticsearchRedisConfig (ES缓存)         ││          │
│  │  → r-j6c45cmtow120vk6fe.redis.rds         ││          │
│  └───────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

### 1.2 数据源路由规则

| 数据源 | 注解 | 使用方 |
|------|------|-------|
| master (sphere2-contract) | 默认(无注解) | 30+ ServiceImpl(contract/subcontract/so/action...) |
| sim_db | `@DS("sim_db")` | SimMapper, SimServiceImpl, SimEventMapper, SlsSimEventManagerImpl |
| billing_db | `@DS("billing_db")` | SimBillingSupportManager |

### 1.3 ⚠️ 已知陷阱: @Transactional + @DS 冲突

**根因**: baomidou dynamic-datasource 的 `@DS` 注解**无法在活跃的 `@Transactional` 事务内切换数据源**。

**影响范围**: 所有通过 `@Transactional` 方法调用 `@DS("sim_db")` / `@DS("billing_db")` 的场景。

**受影响类** (已发现):
| 类 | 方法 | @Transactional | 调用的@DS方法 |
|------|------|:--:|------|
| ~~CancelBundleService~~ | ~~cancelBundle~~ | ❌已移除 | simService.getBySimIccid |
| ~~SimApiSupportServiceImpl~~ | ~~cancel~~ | ❌已移除 | simService.getBySimIccid |
| BuildContractService | saveSimAndContract | ✅仍存在 | simService.save/updateBySimIccid |
| OrderBundleService | orderBundle | ✅仍存在 | simService.updateBySimIccid |

### 1.4 Redis 连接架构

| 配置类 | 连接工厂 | 用途 | 连接池 |
|------|------|------|:--:|
| RedisConfig | contractRedisTemplate | 主业务缓存 | 默认 |
| RedisConfig | container (RedisMessageListenerContainer) | **无监听器的僵尸容器** | 1连接 |
| ExpireEventRedisConfig | expireRedisTemplate | 过期事件 | 默认 |
| ElasticsearchRedisConfig | elasticsearchLettuceConnectionFactory | ES缓存 | max-total:200 |

**⚠️ 已知问题**: `RedisMessageListenerContainer` 无注册监听器但依然打开 Redis 连接。已在 v1.8.9-alpha.2 添加 `@PreDestroy`。

---

## 二、Bug 案例库

### Bug #1: CancelActionServiceImpl — @Transactional阻止@DS数据源切换 🔴

| 属性 | 值 |
|------|-----|
| **Jira** | PR-6672 |
| **发现时间** | 2026-05-16 |
| **影响** | 55张卡 cancel 全部失败 (5/15 17:11 ~ 5/16 10:06) |
| **根因类别** | DEPENDENCY (baomidou @DS + Spring @Transactional 冲突) |
| **级别** | L3 (业务逻辑变更) |

**调用链**:
```
CancelActionServiceImpl.processCancel() [MQ Consumer]
  → CancelBundleService.cancelBundle() [@Transactional → 默认数据源]
    → SimServiceImpl.getBySimIccid() [@DS("sim_db") ← 无法切换!]
      → SimMapper.selectOne() → ❌ Table 'sphere2-contract.sim' doesn't exist
```

**修复**:
1. `CancelBundleService.cancelBundle()` 移除 `@Transactional`
2. `SimApiSupportServiceImpl.cancel()` 移除 `@Transactional`
3. `TestController` 新增 `POST /retryCancelBundle` 补偿接口

**预防**:
- 所有 `@Transactional` 方法内禁止调用 `@DS("sim_db")` / `@DS("billing_db")`
- 如需事务+多数据源: 使用 `@Transactional(propagation = REQUIRES_NEW)` 或用编程式事务

---

### Bug #2: 新Pod启动Redis连接超时 — 连接池未优雅关闭 🔴

| 属性 | 值 |
|------|-----|
| **Jira** | PR-6674 |
| **发现时间** | 2026-05-16 |
| **影响** | 8次重启全部失败，新Pod无法启动 |
| **根因类别** | INFRA+CODE (K8s RollingUpdate + Redis 连接未优雅关闭) |
| **级别** | L2 (连接管理) |

**调用链**:
```
K8s RollingUpdate → 旧Pod SIGTERM
  → Spring shutdown → RedisMessageListenerContainer.destroy() 可能阻塞
  → 30s超时 → K8s SIGKILL → TCP连接TIME_WAIT残留
  → Redis maxclients 被占满
  → 新Pod启动 → Unable to connect to Redis
```

**修复**:
1. `RedisConfig` 新增 `@PreDestroy destroy()` — 显式 stop+destroy
2. `ElasticsearchRedisConfig` 新增 `.shutdownTimeout(Duration.ofSeconds(2))`

**快速诊断命令**:
```bash
# 检查Redis连接数
redis-cli -h r-j6c45cmtow120vk6fe.redis.rds.aliyuncs.com -p 6379 INFO clients | grep connected_clients

# 检查Pod重启次数
kubectl get pods -n sphere2 | grep contract | awk '{print $4}'
```

---

### Bug #3: MnoGatewayCommonListener consume exception:null 🟡

| 属性 | 值 |
|------|-----|
| **Jira** | PR-6649 |
| **根因类别** | CODE (K002日志级别 + K003 printStackTrace) |

**修复**: `e.getMessage()` null → 参数化日志 + 移除 `e.printStackTrace()`

---

## 三、快速诊断指南

### 3.1 SLS 搜索模式

| 问题 | SLS 查询 |
|------|---------|
| Cancel 失败 | `"cancel error"` |
| SQL sim 表不存在 | `"sphere2-contract.sim" OR "doesn't exist"` |
| Redis 连接失败 | `"Unable to connect to Redis"` |
| MnoGateway 错误 | `"MnoGatewayCommonListener"` |

### 3.2 DMS 验证命令

```bash
# 查看某卡 cancel 状态
SELECT sim_iccid, execute_result, execute_result_code, created_at
FROM action_detail_cancel WHERE sim_iccid = '{iccId}' ORDER BY created_at DESC LIMIT 5;

# 查看某卡所有 action
SELECT 'cancel' t, execute_result, created_at FROM action_detail_cancel WHERE sim_iccid='{iccId}'
UNION ALL SELECT 'suspend', execute_result, created_at FROM action_detail_suspend WHERE sim_iccid='{iccId}'
UNION ALL SELECT 'resume', execute_result, created_at FROM action_detail_resume WHERE sim_iccid='{iccId}';
```

### 3.3 常见启动问题

| 症状 | 可能原因 | 检查 |
|------|---------|------|
| Failed to start bean 'container' | Redis连接超时 | Redis实例可达性/安全组 |
| 连续重启8次+ | 疑似连接泄漏 | Redis maxclients / Pod日志 |
| 旧Pod正常新Pod失败 | 镜像版本差异 | `docker diff` 或 `pom.xml` 对比 |

---

## 四、服务扫描记录

| 日期 | Jira | 发现 | 修复 | 状态 |
|------|------|------|------|:--:|
| 2026-05-15 | PR-6653 | SQL sim不存在 + MnoGatewayListener null | — | ⚠️ |
| 2026-05-15 | PR-6649 | MnoGatewayListener 日志修复 | ✅ | ✅已合并 |
| 2026-05-16 | PR-6671 | 2类错误全量 (稳定版扫描) | 前序PR已覆盖 | ⚠️待部署 |
| 2026-05-16 | PR-6672 | cancel全部失败 (@Transactional+@DS) | ✅ | ✅已合并,master-new |
| 2026-05-16 | PR-6674 | 新Pod Redis连接失败 (连接池泄漏) | ✅ | ✅已合并,master-new |
