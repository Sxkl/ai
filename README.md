# OpenCode Agents — Production-Grade Multi-Agent Orchestration Platform

基于 [OpenCode](https://opencode.ai) 的生产级多 Agent 协作系统，用于自动化生产故障排查与修复。

## 架构概览

```
User → Coordinator (DAG Scheduler)
         │
         ├─ Layer 0:        [Git Prep] ────── [SLS Scan]
         ├─ Layer 1:        [Jira Create] ─── [DB Check]
         ├─ Layer 2:        [Analyze Root Cause]  ← Dual Memory + Metacognitive
         ├─ Layer 3:        [Code Fix]            ← Self-Improvement Loop
         ├─ Layer 4-5:      [R1/R2/R3 Review]    ← Scoring + Feedback
         ├─ Layer 5a:       [Quality Gate]        ← score >= 7? → loop back
         ├─ Layer 6:        [Deploy + MR]
         ├─ Layer 7:        [Report Backfill]
         └─ Layer 8:        [Verify]
```

## 核心理念 (v3.1)

从 [all-agentic-architectures](https://github.com/FareedKhan-dev/all-agentic-architectures) 仓库中学习的三个原则：

### 1. 迭代优于单次 (Self-Improvement Loop)
- `fix → review → score < 7 → fix(revision) → review`
- 最多 3 轮迭代, 每轮针对性修订
- 质量不达标不交付

### 2. 记忆优于无状态 (Dual Memory)
- **Episodic Memory**: 相似历史案例检索
- **Semantic Memory**: 知识库模式匹配 (index.md)
- 自动沉淀新案例到知识库

### 3. 自知优于盲动 (Metacognitive)
- Agent 自我模型: 能力边界 + 局限
- 置信度评估: AUTO_FIX / NEEDS_HUMAN / ESCALATE
- 不确定的问题主动上报人类

## Agent 目录

| Agent | 功能 | 版本 |
|-------|------|:----:|
| `coordinator` | DAG 调度 + 规则引擎 | v3.1 |
| `analyze-agent` | 根因分析 + 双记忆 + 元认知 | v3 |
| `fix-agent` | 代码修复 + 迭代修订 | v3 |
| `review-agent` | 三轮审查 + 评分 + 反馈循环 | v3 |
| `decision-engine` | 多模型 5 轮辩论 | v2 |
| `test-agent` | 自动测试生成与验证 | v3 |
| `deploy-agent` | Git 提交 + MR 创建 | v2 |
| `jira-agent` | Jira 创建 + 回填 | v4 |
| `sls-agent` | SLS 日志全量拉取 | v3 |
| `db-agent` | DMS 数据库验证 | v2 |
| `io-agent` | Git 准备 + 分支创建 | v2 |
| `cost-tracker` | Token/API 成本追踪 | v2 |
| `skill-executor` | Skills DAG 执行引擎 | v1 |
| `workflow-driver` | AI-Native 开发工作流 | v1 |
| `sls-log-analysis` | 全级别日志梳理分析 | v1 |
| `production-incident-fix` | 生产故障排查修复 | v2 |

## 技术栈

- **框架**: OpenCode (Claude Sonnet / GPT / DeepSeek / Kimi 多模型)
- **知识库**: Markdown + YAML frontmatter + 相似度搜索
- **工具集成**: SLS (阿里云日志), Jira, GitLab, DMS (数据库)
- **质量保证**: 3 轮代码审查 + 5 轮模型辩论 + 质量门禁

## 快速开始

1. 安装 OpenCode CLI
2. 将本仓库克隆到 `~/.config/opencode/`
3. 配置 `.env` 中的 API keys
4. 配置 `known-services.yaml` 中的服务列表
5. 运行: `opencode` → 输入故障服务名 + P4 编号

## 相关资源

- [OpenCode 文档](https://opencode.ai)
- [Agentic Architectures 参考](https://github.com/FareedKhan-dev/all-agentic-architectures)
- [详细分析报告](agentic-architectures-analysis.md)
