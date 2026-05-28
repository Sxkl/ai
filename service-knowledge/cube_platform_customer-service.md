---
service: customer-service
group: cube/platform
repo: https://git.io.linksfield.net/cube/platform/customer-service
---

# customer-service — 服务架构文档

## 1. 基本信息

customer-service 是 cube 平台客户管理服务，负责客户信息管理、品牌配置、客户层级关系、定时短信任务调度、CRM 集成等业务。

| 属性 | 值 |
|------|-----|
| 框架 | Spring Boot (CustomerServiceApplication.java) |
| 包结构 | 标准分层 |
| 端口 | 标准 Spring Boot |
| 部署 | K8s (ACK) |

## 2. 技术栈

| 组件 | 用途 | 配置类 |
|------|------|--------|
| Spring Boot | 主框架 | CustomerServiceApplication.java |
| MyBatis-Plus | ORM / 数据库访问 | XML Mapper (SimMapper.xml, TenantAllowedOriginMapper.xml) |
| Redis | 缓存 | RedisConfig, RedisUtils |
| OSS (阿里云) | 对象存储 | OssClientConfiguration, OssConfig |
| Email | 邮件发送 | EmailConfig |
| Feign (OpenFeign) | 微服务 RPC | CubeServerFeignClient, Sphere2LeoOrganizationalFeign, IdPortalFeign (含 fallback) |
| Quartz | 定时任务调度 | SmsSendingJob, TaskLoader |
| JWT | 认证拦截 | JwtInterceptor |
| Async | 异步执行 | AsyncConfig, DomainConfigurerAsync |
| TransactionTemplate | 编程式事务 | TransactionTemplateConfig |

## 3. 数据库

- ORM: MyBatis-Plus + XML Mapper
  - SimMapper.xml
  - TenantAllowedOriginMapper.xml
- 主要涉及：客户、品牌配置、定时任务、短信调度、操作日志等业务表
- 数据源：Spring Boot 标准配置

## 4. 缓存 Redis

- RedisConfig: Redis 连接配置
- RedisUtils: Redis 操作工具类
- 用途：客户信息缓存、短信任务状态缓存、JWT token 黑名单等

## 5. 存储 OSS

- OssClientConfiguration / OssConfig: 阿里云 OSS 配置
- 用途：客户附件、短信任务报表文件、品牌配置图片等存储

## 6. API 端点

### Controllers

| Controller | 职责 |
|------------|------|
| BrandConfigController | 品牌配置管理 |
| CrmCustomerController | CRM 客户信息同步 |
| CustomerController | 客户基础信息 CRUD |
| ScheduledTaskController | 定时任务管理 |
| SmsCronExecutionTimesController | 短信 Cron 执行次数管理 |
| SmsScheduledOperationLogController | 短信调度操作日志 |
| SmsScheduledSimController | 短信调度 SIM 关联 |
| SmsScheduledTaskDetailController | 短信调度任务详情 |
| SmsTaskEmailController | 短信任务邮件通知 |
| TenantAllowedOriginController | 租户允许来源配置 |

### Services 业务层

| Service | 职责 |
|---------|------|
| BrandConfigService | 品牌配置业务 |
| CrmCustomerService | CRM 客户集成 |
| CustomerHierarchyService | 客户层级关系管理 |
| DomainAsyncTaskService | 域异步任务处理 |
| EmailPostService | 邮件发送 |
| OssStorageService | OSS 存储操作 |
| ScheduledTaskService | 定时任务业务 |
| SmsCronService | 短信 Cron 调度 |
| SmsScheduledService | 短信定时调度核心 |
| TenantAllowedOriginService | 租户来源白名单 |
| UserService | 用户服务 |

### Entities 实体

| Entity | 说明 |
|--------|------|
| BrandConfig | 品牌配置 |
| DomainAsyncTask | 域异步任务 |
| ScheduledTask | 定时任务 |
| SmsCronExecutionTimes | 短信 Cron 执行次数 |
| SmsScheduledOperationLog | 短信调度操作日志 |
| SmsScheduledSim | 短信调度 SIM 关联 |
| SmsScheduledTask | 短信调度任务 |
| SmsScheduledTaskDetail | 短信调度任务详情 |
| TenantAllowedOrigin | 租户允许来源 |

### Feign Clients (下游调用)

| Feign Client | 下游服务 | Fallback | 用途 |
|-------------|----------|----------|------|
| CubeServerFeignClient | Cube Server | 有 | Cube 平台服务调用 |
| Sphere2LeoOrganizationalFeign | Sphere2 组织服务 | 有 | 组织结构信息同步 |
| IdPortalFeign | ID Portal | 有 | 身份认证/用户信息 |

说明：三个 Feign Client 均有 fallback 实现，具备降级容错能力。

## 7. 定时任务 (Quartz)

- SmsSendingJob: 短信发送任务（Quartz Job）
- TaskLoader: 任务加载器（动态加载/注册 Quartz 任务）
- SmsCronExecutionTimes: 记录 Cron 表达式执行次数

Quartz 用于管理动态定时任务，主要用于短信定时发送场景。

## 8. 异步处理

- AsyncConfig: 异步配置（@EnableAsync, 线程池配置）
- DomainConfigurerAsync: 域配置异步处理

## 9. JWT 认证

- JwtInterceptor: JWT 拦截器（API 认证/鉴权）

## 10. 依赖关系

```
customer-service
  ├── 依赖: Cube Server ← Feign (CubeServerFeignClient, 有 fallback)
  ├── 依赖: Sphere2 Organization ← Feign (Sphere2LeoOrganizationalFeign, 有 fallback)
  ├── 依赖: ID Portal ← Feign (IdPortalFeign, 有 fallback)
  ├── 依赖: Redis (RedisConfig + RedisUtils)
  ├── 依赖: OSS (OssClientConfiguration + OssConfig)
  ├── 依赖: Email (EmailConfig)
  ├── 依赖: Quartz Scheduler (内嵌)
  └── 依赖: MySQL (MyBatis-Plus + XML Mapper)
```

## 11. 已知陷阱

1. **Quartz 集群模式**：如果多实例部署，Quartz 需配置集群模式（JDBC JobStore），否则同一 Job 会在多节点重复执行。
2. **XML Mapper 位置**：使用 XML Mapper（SimMapper.xml, TenantAllowedOriginMapper.xml），注意 mybatis-plus.mapper-locations 配置路径正确。
3. **Feign Fallback 实现**：三个 Feign Client 都有 fallback，但需确保 fallback 逻辑合理（返回默认值 vs 抛出业务异常），避免吞掉关键错误。
4. **JWT 拦截器**：JwtInterceptor 需注意排除不需要认证的端点（如健康检查），并处理 token 过期刷新机制。
5. **异步任务事务**：TransactionTemplateConfig 提供了编程式事务，在 @Async 方法中使用时注意事务传播行为，异步方法的事务是独立的。
6. **短信调度**：SmsSendingJob + TaskLoader 表明支持动态定时任务，注意 Job 的动态注册/注销的正确性，避免内存泄漏或死 Job。
7. **邮件发送**：EmailConfig 需配置正确的 SMTP 服务器和认证信息，注意邮件发送失败的降级处理（如重试、告警）。
8. **Cron 执行次数**：SmsCronExecutionTimes 记录执行次数，注意此表的数据增长，需定期清理历史数据。
9. **OssClientConfiguration + OssConfig**：两个 OSS 配置类可能对应不同 Bucket 或不同用途，注意区分使用场景。
