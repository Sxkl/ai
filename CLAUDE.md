# OpenCode Agent System — Claude CLI Integration

You have access to a production-grade multi-agent system originally built for OpenCode.
Skills are auto-loaded from `~/.claude/skills/` (symlinked to opencode). Agent definitions
live at `@~/.claude/agents/` and can be referenced for role-specific instructions.

## When to Use Skills vs Agents

- **Skills** trigger automatically based on their description keywords. Read a skill's SKILL.md to see its trigger conditions.
- **Agents** are role definitions. When a task matches an agent's description, read that agent's
  file and adopt its persona, rules, and output format.
- **Knowledge Base** lives at `@~/.claude/skills/../knowledge/index.md` — contains proven fix patterns (K001-K015) and known traps.

## Agent Catalog

| Agent | File | When to Use |
|-------|------|-------------|
| `coordinator` | `@~/.claude/agents/coordinator.md` | Multi-step workflows, DAG scheduling, rule enforcement |
| `analyze-agent` | `@~/.claude/agents/analyze-agent.md` | Root cause analysis with dual memory + metacognitive assessment |
| `fix-agent` | `@~/.claude/agents/fix-agent.md` | Code fixes with self-improvement loop (max 3 revisions) |
| `review-agent` | `@~/.claude/agents/review-agent.md` | 3-round code review (compile → thread safety → production) with scoring |
| `decision-engine` | `@~/.claude/agents/decision-engine.md` | Multi-model debate (3-5 rounds depending on complexity) |
| `test-agent` | `@~/.claude/agents/test-agent.md` | Auto-generate and run unit tests |
| `deploy-agent` | `@~/.claude/agents/deploy-agent.md` | Git commit + push + MR creation |
| `jira-agent` | `@~/.claude/agents/jira-agent.md` | Jira issue creation and report backfill |
| `sls-agent` | `@~/.claude/agents/sls-agent.md` | SLS log pulling and analysis |
| `db-agent` | `@~/.claude/agents/db-agent.md` | DMS database validation |
| `io-agent` | `@~/.claude/agents/io-agent.md` | Git repo cloning and branch creation |
| `cost-tracker` | `@~/.claude/agents/cost-tracker.md` | Token/API cost tracking |
| `workflow-driver` | `@~/.claude/agents/workflow-driver.md` | AI-Native TDD development loop |

## Production Incident Fix Pipeline (DAG)

When a production error is reported, follow this pipeline (from coordinator.md):

```
Layer 0: git-prep + sls-scan          (parallel)
Layer 1: jira-create + db-check       (parallel, db conditional)
Layer 2: analyze-root-cause           (memory retrieval → metacognitive)
Layer 3: code-fix
Layer 4: r1-compile + r2-thread + test (parallel)
Layer 5: r3-production + quality-gate
Layer 5a: [score < 7? → loop back to Layer 3, max 3x]
Layer 6: deploy-mr
Layer 7: report-backfill
Layer 8: verify
```

## Three Core Principles (v3.1)

1. **迭代优于单次**: fix → review → score < 7 → fix(revision) → ... max 3 rounds
2. **记忆优于状态**: search knowledge base (index.md patterns) before analyzing
3. **自知优于盲动**: metacognitive check — AUTO_FIX / NEEDS_HUMAN / ESCALATE based on confidence

## Quick Reference: Knowledge Base Patterns

- `@~/.claude/skills/../knowledge/index.md` — Full pattern index (K001-K015, U001-U005)
- K001: Jackson unknown field → `@JsonIgnoreProperties`
- K003: printStackTrace → `log.error(msg, e)`
- K009: parallelStream NPE → null check before
- K013: Redis lock leak → Lua atomic release
- U001-U005: Unrepairable patterns (upstream/config/data issues)

## Tool Integration

When using MCP tools from the stargate server:
- SLS log queries → use `Sls-20201230-` tools
- Jira operations → use `jira_` tools  
- GitLab operations → use `stargate_gitlab_` tools
- Database schema → use `stargate_pltdb_` tools
- DMS SQL → use `dms-sql` skill
