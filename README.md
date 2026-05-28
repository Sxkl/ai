# OpenCode Agent System

Production-grade multi-agent orchestration platform. Two independent copies that evolve separately and learn from each other.

## 目录结构

```
├── opencode/                     ← ~/.config/opencode/ 独立副本
│   ├── agents/                   ← 16 个生产级 agent 定义
│   ├── skills/                   ← 25 个 skill
│   ├── knowledge/                ← 知识库 (K001-K015 + SOP)
│   ├── rag/                      ← RAG 向量检索配置
│   └── opencode.json             ← OpenCode 配置
│
├── claude/                       ← ~/.claude/ 独立副本
│   ├── agents/                   ← 同一套 agents
│   ├── skills/                   ← 同一套 skills
│   ├── knowledge/                ← 同一套知识库
│   ├── CLAUDE.md                 ← Claude CLI 协调器
│   └── settings.json             ← Claude CLI 配置
│
├── agentic-architectures-analysis.md  ← 架构学习分析报告
└── README.md
```

## 相互学习规则

两套副本各自演化。当一边有改进时，**手动**同步到另一边：

```bash
# 查看两边差异
diff -rq opencode/agents/ claude/agents/
diff -rq opencode/skills/ claude/skills/

# 从 opencode 同步到 claude
rsync -av opencode/agents/ claude/agents/
rsync -av opencode/skills/ claude/skills/

# 从 claude 同步到 opencode
rsync -av claude/agents/ opencode/agents/
rsync -av claude/skills/ opencode/skills/
```

## 三大核心原则 (v3.1)

1. **迭代优于单次**: fix → review → score < 7 → fix(revision) → max 3 rounds
2. **记忆优于状态**: 分析前先查 knowledge/index.md 中的已知模式
3. **自知优于盲动**: 元认知检查 → AUTO_FIX / NEEDS_HUMAN / ESCALATE

## Agent 列表

| Agent | 功能 | 版本 |
|-------|------|:----:|
| `coordinator` | DAG 调度 + 规则引擎 (Skill Executor) | v3.1 |
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

## 灵感来源

- [all-agentic-architectures](https://github.com/FareedKhan-dev/all-agentic-architectures) — 17 种现代 Agent 架构的教学实现
- Self-Improvement Loop (RLHF)
- Episodic + Semantic Memory
- Reflexive Metacognitive
