# OpenCode Agent System — Claude CLI 独立副本

⚠️ 本目录 (`~/.claude/`) 是 `~/.config/opencode/` 的**独立副本**。两套各自演化，发现问题后**相互学习**、分别修改。

## 目录结构

```
~/.config/opencode/          ~/.claude/
├── agents/     ←──────────→ ├── agents/      (独立副本)
├── skills/     ←──────────→ ├── skills/      (独立副本)
├── knowledge/  ←──────────→ ├── knowledge/   (独立副本)
└── opencode.json             └── CLAUDE.md
```

## 相互学习规则

当在 **opencode** 中发现更好的配置/修复/知识 → 手动同步到 `~/.claude/`
当在 **Claude CLI** 中发现更好的配置/修复/知识 → 手动同步到 `~/.config/opencode/`

```bash
# 查看两边差异
diff -rq ~/.config/opencode/agents/ ~/.claude/agents/
diff -rq ~/.config/opencode/skills/ ~/.claude/skills/
diff -rq ~/.config/opencode/knowledge/ ~/.claude/knowledge/

# 从 opencode 同步到 claude
rsync -av ~/.config/opencode/agents/ ~/.claude/agents/
rsync -av ~/.config/opencode/skills/ ~/.claude/skills/
rsync -av ~/.config/opencode/knowledge/ ~/.claude/knowledge/

# 从 claude 同步到 opencode
rsync -av ~/.claude/agents/ ~/.config/opencode/agents/
rsync -av ~/.claude/skills/ ~/.config/opencode/skills/
rsync -av ~/.claude/knowledge/ ~/.config/opencode/knowledge/
```

## Agent Catalog

阅读对应 agent 文件来切换角色：

| Agent | 文件 | 何时使用 |
|-------|------|-------------|
| `coordinator` | `@~/.claude/agents/coordinator.md` | 多步工作流、DAG 调度、规则执行 |
| `analyze-agent` | `@~/.claude/agents/analyze-agent.md` | 根因分析（双记忆+元认知） |
| `fix-agent` | `@~/.claude/agents/fix-agent.md` | 代码修复（Self-Improvement Loop） |
| `review-agent` | `@~/.claude/agents/review-agent.md` | 3轮审查（编译→线程→生产） |
| `decision-engine` | `@~/.claude/agents/decision-engine.md` | 多模型辩论（3-5轮） |
| `test-agent` | `@~/.claude/agents/test-agent.md` | 自动测试生成 |
| `deploy-agent` | `@~/.claude/agents/deploy-agent.md` | Git 提交 + MR |
| `jira-agent` | `@~/.claude/agents/jira-agent.md` | Jira 工单管理 |
| `sls-agent` | `@~/.claude/agents/sls-agent.md` | SLS 日志拉取 |
| `db-agent` | `@~/.claude/agents/db-agent.md` | 数据库校验 |
| `io-agent` | `@~/.claude/agents/io-agent.md` | Git 仓库操作 |
| `cost-tracker` | `@~/.claude/agents/cost-tracker.md` | 成本追踪 |
| `workflow-driver` | `@~/.claude/agents/workflow-driver.md` | AI-Native TDD 循环 |
| `code-wiki-agent` | `@~/.claude/agents/code-wiki-agent.md` | 代码知识库（扫描/问答/架构图/影响分析） |

## 生产故障修复 Pipeline (DAG)

```
Layer 0: git-prep + sls-scan          (并行)
Layer 1: jira-create + db-check       (并行, db 条件触发)
Layer 2: analyze-root-cause           (记忆检索 → 元认知)
Layer 3: code-fix                     (Self-Improvement Loop)
Layer 4: r1-compile + r2-thread + test (并行)
Layer 5: r3-production + quality-gate
Layer 5a: [score < 7? → 回到 Layer 3, 最多 3 轮]
Layer 6: deploy-mr
Layer 7: report-backfill
Layer 8: verify
```

## 三大核心原则 (v3.1)

1. **迭代优于单次**: fix → review → score < 7 → fix(revision) → ... max 3 rounds
2. **记忆优于状态**: 分析前先查 knowledge/index.md 中的已知模式
3. **自知优于盲动**: 元认知检查 → AUTO_FIX / NEEDS_HUMAN / ESCALATE

## 知识库快速索引

- `@~/.claude/knowledge/index.md` — 完整模式索引 (K001-K015, U001-U005)
- K001: Jackson unknown field → `@JsonIgnoreProperties`
- K003: printStackTrace → `log.error(msg, e)`
- K009: parallelStream NPE → null check before
- K013: Redis lock leak → Lua atomic release
- U001-U005: 不可修复模式 (upstream/config/data)

## 工具集成

- SLS 日志 → `Sls-20201230-` 工具
- Jira → `jira_` 工具
- GitLab → `stargate_gitlab_` 工具
- 数据库 → `stargate_pltdb_` 工具
