---
service: contract-service
group: cube/platform
repo: https://git.io.linksfield.net/cube/platform/contract-service
---

# contract-service — 服务架构文档

## 1. 基本信息

contract-service 是 cube 平台合同/套餐/资费生命周期管理服务，管理套餐订购、变更、转移、退订等全流程，并负责 CDR 话单处理与计费相关业务。

| 属性 | 值 |
|------|-----|
| 框架 | Spring Boot (ContractApplication.java) |
| 包结构 | 按业务域分层 |
| 端口 | 标准 Spring Boot |
| 部署 | K8s (ACK) |

## 2. 技术栈

| 组件 | 用途 | 配置类 |
|------|------|--------|
| Spring Boot | 主框架 | ContractApplication.java |
| MyBatis-Plus | ORM / 数据库访问 | MybatisPlusConfig.java |
| Flyway | 数据库迁移 | db/migration/ |
| Redis | 缓存 / 分布式锁 | RedisConfig, expired/redission/ |
| RocketMQ | 消息队列 | rocketmq/ 含 interceptor/ |
| Elasticsearch | 全文搜索 | EsConfig, EsIndex |
| Apache POI | Excel 导入导出 | POI 配置 |
| RestTemplate | HTTP 同步调用 | RestTemplateConfig |
| Feign (OpenFeign) | 微服务 RPC | CustomFeignInterceptor + 大量 Feign Clients |
| Disruptor | 高性能事件处理 | event/disruptor/ |
| SLS (阿里云) | 日志 | SLS 配置 |
| ThreadPool | 线程池 | ThreadPool 配置 |

## 3. 数据库

- ORM: MyBatis-Plus (MybatisPlusConfig.java)
- 迁移: Flyway (db/migration/)
- 主要涉及：合同、套餐、订购、变更、转移、退订、CDR 话单等业务表
- 数据源：Spring Boot 标准配置

## 4. 缓存 Redis

| 配置 | 用途 |
|------|------|
| RedisConfig | 默认缓存配置 |
| expired/redission/ | Redisson 分布式锁、过期 key 事件处理 |

- 用途：合同状态缓存、套餐信息缓存、分布式锁（防止并发操作同一合同）

## 5. 消息队列

- MQ: RocketMQ (rocketmq/ 目录)
- 拦截器: rocketmq/interceptor/（消息拦截/过滤）
- 用途：合同状态变更事件广播、套餐变更通知、CDR 话单异步处理等

## 6. 搜索 Elasticsearch

- EsConfig: ES 客户端配置
- EsIndex: ES 索引管理
- 用途：合同/套餐/话单数据的全文搜索与分析

## 7. API 端点

### Controllers

| 目录 | 职责 |
|------|------|
| action/ | 合同操作（创建、变更、续约、退订等） |
| api/ | 对外 API 接口 |
| diagnosis/ | 诊断接口（问题排查、数据修复） |

### Services 业务层

| 目录 | 职责 |
|------|------|
| actions | 合同操作业务逻辑 |
| base | 基础服务层 |
| biz/ | 核心业务 |
| biz/api | 对外 API 业务 |
| biz/contract | 合同核心业务 |
| biz/imsi | IMSI 相关业务 |
| biz/sim | SIM 相关合同业务 |
| biz/sms | 短信相关业务 |
| biz/subcontract | 子合同/分合同业务 |
| biz/transfer | 合同转让/转移 |
| cdr | CDR 话单处理 |
| convert | 数据转换 |
| cube | Cube 平台集成 |
| es | ES 操作服务 |
| excel | Excel 导入导出 |
| feign | Feign 调用封装 |
| history | 历史数据处理 |
| listener | 消息/事件监听 |
| migration | 数据迁移 |
| mq | MQ 操作封装 |
| notification | 通知服务 |
| query | 查询服务 |

### Feign Clients (下游调用)

| Feign Client | 下游服务 | 用途 |
|-------------|----------|------|
| bbc | BBC 服务 | BBC 业务集成 |
| billing | 计费服务 | 计费查询/操作 |
| consumer | 消费者服务 | 消费者信息 |
| cube | Cube 服务 | Cube 平台调用 |
| customer | 客户服务 | 客户信息查询 |
| custsku | 客户 SKU 服务 | SKU 管理 |
| scm | 供应链服务 | SCM 集成 |
| sku | SKU 服务 | 产品 SKU |
| so | 销售订单服务 | 订单管理 |
| wms | 仓储服务 | WMS 集成 |

- 拦截器: CustomFeignInterceptor（统一 Feign 请求拦截，如添加认证头、TraceId）

## 8. Disruptor 事件处理

- event/disruptor/：基于 LMAX Disruptor 的高性能事件处理框架
- 用途：高吞吐量场景（可能用于 CDR 话单或合同事件的批量处理），RingBuffer 无锁并发

## 9. 依赖关系

```
contract-service
  ├── 依赖: bbc (BBC 服务) ← Feign
  ├── 依赖: billing (计费服务) ← Feign
  ├── 依赖: consumer (消费者服务) ← Feign
  ├── 依赖: cube (Cube 服务) ← Feign
  ├── 依赖: customer (客户服务) ← Feign
  ├── 依赖: custsku (客户 SKU) ← Feign
  ├── 依赖: scm (供应链) ← Feign
  ├── 依赖: sku (SKU 服务) ← Feign
  ├── 依赖: so (销售订单) ← Feign
  ├── 依赖: wms (仓储) ← Feign
  ├── 依赖: Redis
  ├── 依赖: RocketMQ
  ├── 依赖: Elasticsearch
  └── 依赖: MySQL (MyBatis-Plus)
```

## 10. 定时任务

- 推断存在（基于历史/迁移/mq 目录结构）
- 可能的任务：合同到期处理、套餐续约提醒、CDR 数据归档、历史数据清理

## 11. 已知陷阱

1. **Feign 调用链长**：依赖多达 10 个下游服务，任何下游服务不可用都会影响合同流程。注意 Hystrix/Sentinel 熔断降级配置和超时设置。
2. **Disruptor 使用**：Disruptor 是高性能但易出错的框架。注意：
   - RingBuffer 大小配置（必须为 2 的幂）
   - 事件处理异常时的处理策略
   - 避免在 EventHandler 中做阻塞 I/O 操作
3. **合同状态机**：合同/套餐有复杂的状态流转（创建→生效→变更→续约→退订→过期），注意状态机的一致性和并发控制。
4. **RocketMQ 消息顺序**：合同变更事件如果依赖消息顺序，需配置顺序消息。
5. **Redis 过期事件**：expired/redission/ 目录表明使用了 Redis key 过期监听，注意 Redis 的过期通知机制不可靠（可能丢失或延迟）。
6. **数据迁移**：migration/ 服务目录表明存在数据迁移逻辑，注意迁移过程的幂等性和回滚方案。
7. **CustomFeignInterceptor**：自定义 Feign 拦截器中添加的请求头（如认证 token、TraceId）注意线程安全，避免使用实例变量。
8. **RestTemplate**：存在 RestTemplateConfig，注意与 Feign 的分工，避免滥用 RestTemplate 做同步阻塞调用。
