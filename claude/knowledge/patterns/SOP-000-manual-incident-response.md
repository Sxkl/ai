# SOP-000: 被动问题发现快速处理流程 (Manual Incident Response)

> **版本**: v1.0 | **日期**: 2026-05-16 | **触发**: 人工报告 / 用户反馈 / 手动指定  
> **与自动扫描的关系**: 互补 — 不改自动扫描, 处理自动扫描发现不了的深度问题

---

## 流程对比

| 维度 | 自动扫描 (Auto-Scan) | 被动发现 (Manual) |
|------|:---:|:---:|
| **触发** | 定时/按排名 | 人工报告/用户指定 |
| **SLS** | 全量分页(7天) | 聚焦指定时间段 |
| **分类** | 全量归集所有错误 | 聚焦指定错误类型 |
| **知识库** | 匹配后自动修复 | 匹配加速诊断 |
| **裁决** | 5轮多模型辩论 | 3轮快速确认 |
| **DMS** | 仅SQL错误时触发 | 按需查询验证 |
| **Jira** | 详细模板+MD附件 | 轻量级(聚焦修复) |
| **输出** | 8段报告+MR | curl命令+DMS数据+修复 |

---

## 被动发现 7 步 SOP

### Step 1: 接收并分类

```
用户输入 → 提取关键信息:
  - 服务名? (contract-service)
  - 问题类型? (启动失败 / 接口报错 / 数据异常)
  - 时间范围? (刚才 / 今天 / 某个时间段)
  - 是否紧急? (生产故障 / 预发布验证)
```

### Step 2: SLS 快速诊断

```
拉取指定时间窗口日志:
  - 启动问题 → "Application run failed" OR "Started ContractApplication"
  - 接口报错 → 指定方法名 + "ERROR" 
  - 数据异常 → 指定关键词 + "Exception"
  
对比分析:
  - 旧Pod vs 新Pod (镜像版本差异)
  - 正常时间段 vs 异常时间段
  - 不同节点上的Pod
```

### Step 3: 源码定位

```
grep → 定位错误对应的源码文件
read → 理解调用链和业务逻辑
对比 → 正常流程 vs 异常流程的区别
```

### Step 4: DMS 验证 (按需)

```
条件触发:
  - SQL相关错误 → 验证表结构
  - 业务数据问题 → 查询action_detail表
  - 需要确认数据一致性 → 批量查询验证
  
工具:
  aliyun CLI DMS (profile dms)
  或 pltdb describe_table
```

### Step 5: 代码修复

```
修复原则:
  - 先修复根因(如移除@Transactional)
  - 再加补偿接口(如retryCancelBundle)
  - 再加防御性改进(如@PreDestroy)
  
分支: hotfix/{issue-id}-{service}
标签: 按版本号规则自动递增
合并: → master-new
```

### Step 6: 部署验证

```
SLS 实时监控:
  - 启动成功: "Started ContractApplication"
  - 无报错: 指定错误关键词 count = 0
  - 旧Pod对比: 功能正常

DMS 验证 (如涉及数据):
  - 确认数据状态符合预期
  - 确认无可重复记录
```

### Step 7: 知识沉淀

```
SOP文档 → knowledge/patterns/SOP-XXX.md
服务知识 → knowledge/services/{service}-knowledge.md
修复模式 → knowledge/L{N}/{id}.md
Jira回填 → 根因+修复+验证结果
```

---

## 今天实战案例回顾

### 案例 1: contract-service 新Pod Redis 连接超时

```
Step 1: 用户报告 "服务启动报错"
Step 2: SLS → "Unable to connect to Redis" 6次重启
        对比: 旧Pod(同节点)正常 → 排除网络问题
        发现: v1.8.9 hotfix vs v1.9.0 prod 版本差异
Step 3: grep RedisConfig → 僵尸容器无监听器
        grep ElasticsearchRedisConfig → 无shutdownTimeout
Step 4: (无 DMS)
Step 5: +@PreDestroy + shutdownTimeout(2s)
Step 6: SLS → v1.8.9-alpha.2 启动成功 26s
Step 7: → SOP-002 + contract-service-knowledge.md + PR-6674
```

### 案例 2: CancelActionServiceImpl 55张卡全量失败

```
Step 1: 用户报告 "取消套餐失败"
Step 2: SLS → "cancel error,errorMessage:" 空消息
        拉取全量: 55张卡, 5个时间批次
Step 3: grep @Transactional → CancelBundleService有注解
        grep @DS → SimMapper有注解
        分析法: @Transactionl阻止@DS切换
Step 4: DMS → 5张表扫描, 53安全/2需确认
Step 5: 移除@Transactional + 新增retryCancelBundle
Step 6: curl单张 → SLS 0 error
        curl全量 → SLS 50 retry + 0 error
        DMS → execute_result=1 全部成功
Step 7: → SOP-001 + contract-service-knowledge.md + PR-6672
```

---

## 与自动扫描的协作

```
自动扫描 (定时)          被动发现 (即时)
     │                       │
     │  ┌────────────────────┘
     ▼  ▼
知识库 (共享)
     │
     ├── SOP-001: @Transactional+@DS 冲突 ← 案例2沉淀
     ├── SOP-002: Redis连接池耗尽    ← 案例1沉淀
     ├── contract-service-knowledge  ← 服务陷阱库
     └── K001-K009 + N001-N004      ← 修复模式库
```

## Jira 模板 (被动发现轻量版)

```
## 🐛 {问题标题}

### 根因
{一句话根因 + 调用链}

### 影响
{受影响范围 (卡片数/时间窗口/pod数)}

### 修复
{代码变更清单}

### 验证
{SLS/DMS 验证结果}

### 🔗
{MR/Branch/Tag}
```
