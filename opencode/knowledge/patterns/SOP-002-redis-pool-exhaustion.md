# SOP-002: K8s RollingUpdate Redis连接池耗尽 — 检测修复全流程

> **版本**: v1.0 | **日期**: 2026-05-16 | **可复用**: ✅  
> **触发条件**: 新 Pod 启动后 "Unable to connect to Redis" 但旧 Pod Redis 正常  
> **知识库**: N004 (Redis连接池未优雅关闭)

---

## Phase 1: SLS 检测

### 特征日志
```
ERROR o.s.boot.SpringApplication : Application run failed
WARN ConfigServletWebServerApplicationContext : Exception encountered during context initialization
  → Failed to start bean 'container'
  → RedisConnectionFailureException: Unable to connect to Redis
  → PoolException: Could not get a resource from the pool
  → RedisConnectionException: Unable to connect to r-j6c45cmtow120vk6fe.redis.rds.aliyuncs.com:6379
```

### SLS 查询
```
"Unable to connect to Redis" OR "Failed to start bean 'container'"
```

### 诊断逻辑
```
if old pod (同一个node) Redis正常 AND new pod Redis失败:
    → 排除网络问题(同node共网络)
    → 检查镜像版本差异
    → 检查 Redis maxclients
    → SOP-002 (本流程)
```

---

## Phase 2: 根因分析

### Step 1: 检查 Redis 连接配置

```bash
# 查看有几个 Redis 连接工厂
grep -r "LettuceConnectionFactory\|RedisConnectionFactory" --include="*.java" {service-path} | grep -v test

# 查看 RedisMessageListenerContainer
grep -r "RedisMessageListenerContainer" --include="*.java" {service-path}

# 查看连接池配置
grep -r "maxTotal\|maxIdle\|shutdownTimeout\|shutdownQuietPeriod" --include="*.java" {service-path}
```

### Step 2: 确认关闭链

```
查找 @PreDestroy 或 DisposableBean.destroy() → 是否存在显式关闭?
检查 LettuceClientConfiguration → 是否有 shutdownTimeout?
```

### 根因总结

```
RedisConfig.container (僵尸容器: 无监听器仍开连接)
  → DisposableBean.destroy() 可能阻塞
  → 30s K8s grace period 不够
  → SIGKILL → TCP连接未释放

ElasticsearchRedisConfig 
  → 无 shutdownTimeout → close() 可能无限等待
```

---

## Phase 3: 代码修复

### Fix 1: RedisConfig + @PreDestroy

```java
@PreDestroy
public void destroy() {
    if (container != null) {
        try {
            container.stop();
            container.destroy();
        } catch (Exception e) {
            log.error("error shutting down RedisMessageListenerContainer", e);
        }
    }
}
```

### Fix 2: ElasticsearchRedisConfig + shutdownTimeout

```java
LettuceClientConfiguration clientConfig = LettucePoolingClientConfiguration.builder()
    .commandTimeout(Duration.ofMillis(properties.getTimeout()))
    .poolConfig(poolConfig)
    .shutdownTimeout(Duration.ofSeconds(2))
    .build();
```

---

## Phase 4: 部署 + 验证

### Step 1: 确认新镜像启动

```
SLS: "Started ContractApplication" → 确认启动成功
SLS: "Application run failed" → 检查是否还有 Redis 错误
```

### Step 2: 临时逃生

```bash
# 如果新Pod反复CrashLoopBackOff
kubectl scale deployment {service} -n {ns} --replicas=0
sleep 60  # 等 Redis 释放所有连接
kubectl scale deployment {service} -n {ns} --replicas=2
```

### K8s 验证命令

```bash
kubectl get pods -n sphere2 | grep contract
redis-cli -h {redis_host} -p 6379 INFO clients | grep connected_clients
```

---

## 检查清单 (Level 2 — 4轮裁决)

```
[ ] SLS 确认: 新Pod Redis连接失败, 旧Pod正常
[ ] 检查镜像版本差异
[ ] grep Redis 连接工厂数量
[ ] grep @PreDestroy / shutdownTimeout 是否存在
[ ] 确认 RedisConfig 僵尸容器
[ ] 代码修复: +@PreDestroy + shutdownTimeout
[ ] commit + push + merge
[ ] 部署后 SLS 验证新Pod正常
[ ] Redis connected_clients 确认不增长
```

---

## 案例参考

| 案例 | Jira | 服务 | 影响 | 结果 |
|------|------|------|------|:--:|
| 2026-05-16 | PR-6674 | contract-service | 8次重启 | ✅ 修复后正常 |
