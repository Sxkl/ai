# api-v4-auto-fix Agent 集群

## 概述

针对 cube-api-v4 → k8s-enterprise-gateway → 下游微服务 全链路的自动化日志分析与代码修复 Agent 集群。

基于本次 PR-6836 完整分析流程标准化而来。

## 6-Agent 集群架构

```
                         ┌──────────────────────────────────┐
                         │   Agent 0: Orchestrator          │
                         │   (任务调度 + 超时控制 + 合并)      │
                         └──────────────┬───────────────────┘
                                        │
              ┌─────────────────────────┼──────────────────────┐
              │                         │                      │
    ┌─────────▼─────────┐   ┌──────────▼──────────┐   ┌───────▼───────┐
    │ Agent 1: SLS      │   │ Agent 2: Log        │   │ Agent 3:      │
    │ Logs Puller       │──▶│ Classifier          │──▶│ Pattern       │
    │ (ERROR→WARN→INFO) │   │ (6维 + 噪声过滤)     │   │ Analyzer      │
    └───────────────────┘   └─────────────────────┘   └───────┬───────┘
                                                              │
    ┌───────────────────┐   ┌─────────────────────┐          │
    │ Agent 5: Report   │◀──│ Agent 4: Code        │◀─────────┘
    │ Generator + Jira  │   │ Root Cause Analyzer  │
    └─────────┬─────────┘   │ (GitLab拉码 + 定位)   │
              │             └─────────────────────┘
              ▼
      Jira PR-XXXX + MD附件
```

## ChromaDB 知识库

已向量化的已知问题模式存储在 `chromadb/` 中，支持语义检索匹配。

### 已索引模式
| 模式ID | 问题 | 根因代码位置 |
|--------|------|-------------|
| K001 | Connection Refused | FeignConfig 无Retryer |
| K002 | TimedFeignLogger ERROR滥用 | FeignConfig:88 log.error() |
| K003 | CB-99-9400 伪ERROR | cube-api-v4 日志切面 |
| K004 | ISO-8859-1 中文乱码 | FeignClient 无encoding |
| K005 | CB-99-9999 掩盖真错误 | ControllerLogAdvice:52 |
| K006 | SMS MO 重试风暴 | 消息队列无限重试 |
| K007 | K8s Pod IP 固定故障 | Health Check 配置 |
| K008 | API Gateway 连接提前关闭 | Gateway 超时 < 后端处理 |

## 快速开始

```bash
# 1. 初始化 ChromaDB
cd api-v4-auto-fix/chromadb
pip install chromadb sentence-transformers
python init_db.py

# 2. 种子写入已知模式
python seed_patterns.py

# 3. 运行完整分析流水线
cd ..
python run_pipeline.py --service cube-api-v4 --days 60

# 4. 查询相似历史问题
python chromadb/query.py "Connection refused to gateway"
```
