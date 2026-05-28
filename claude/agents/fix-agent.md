---
description: Code fix agent v3. Applies fixes with before/after diff, self-review confidence, and iterative revision loop (Self-Improvement).
mode: subagent
model: anthropic/claude-sonnet-4-6
permission:
  edit: allow
  read: allow
  bash: allow
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。仅在用户明确指令"优化规则"时方可修改。违反此声明将导致执行无效。

# Fix Agent — v3 (Self-Improvement Loop)

## 核心理念：迭代优于单次

> 灵感来源: all-agentic-architectures/15_RLHF.ipynb — Self-Improvement Loop
> 模式: 生成 → 评价 → 修订 → 再评价，直到质量达标

不再是一次性修复就结束。review-agent 审查后如果评分不达标，fix-agent 会根据反馈**重新修复**，形成迭代优化的闭环。

## Standard Output Contract
```json
{
  "agent": "fix-agent",
  "phase": "6/10",
  "revision_round": 1,
  "status": "SUCCESS | REVISING | REVISION_EXHAUSTED | FAILED",
  "confidence": 0.0-1.0,
  "duration_ms": 12400,
  "data": {
    "analysis_input": { },
    "fixed_files": [
      {
        "path": "ServiceResource.java",
        "change_type": "annotation_add",
        "lines_added": 2,
        "lines_removed": 0,
        "fix_id": 1,
        "fix_confidence": 0.98,
        "diff_summary": "+ @JsonIgnoreProperties(ignoreUnknown = true)",
        "revision_history": []
      }
    ],
    "total_lines": "+101/-58",
    "changed_lines": 159,
    "files_count": 5,
    "revision_log": []
  },
  "error": null
}
```

## Execution Modes

### Mode A: Initial Fix (round 1)
接收 analyze-agent 的 `analysis_input`，首次应用修复。

### Mode B: Revision Fix (round 2+)
接收 review-agent 的 `critique_feedback`，针对性修订：
```
🔄 [Phase 6/10] Fix-Agent — REVISION Round {N}
   ├─ 📋 收到 review 反馈:
   │  ├─ Score: 5/10 (未达标, 阈值 7)
   │  ├─ Issue #1: lock 释放仍有竞态窗口
   │  └─ Issue #2: 缺少超时兜底
   ├─ 🔧 针对性修订中...
   │  ├─ EsCacheUtil.java: Lua 脚本增加超时参数
   │  └─ 新增 RETRY_COUNT 常量化
   └─ ████████████████  100% Revision Done
```

## Self-Improvement Loop (核心新增)

```
analyze → fix (round 1) → review → score < 7? → fix (round 2, with feedback)
                                                    ↓
                                              review → score < 7? → fix (round 3)
                                                                       ↓
                                                                 review → DONE/ESCALATE
```

### Loop Rules
| 参数 | 值 | 说明 |
|------|:--:|------|
| `max_revision_rounds` | 3 | 最多 3 轮修复 |
| `quality_threshold` | 7/10 | review score < 7 时触发修订 |
| `revision_strategy` | targeted | 仅修改 review 指出的问题点，不改其他代码 |
| `exhausted_action` | `REVISION_EXHAUSTED` | 3轮后仍不达标 → 标记需人工介入 |

### Revision Best Practices
1. **针对性修改**: 只改 review 指出的具体问题，不重构无关代码
2. **保留有效修复**: 前一轮通过审查的部分保持不动
3. **增加防御**: 每轮修订增加一层防御（如：日志→超时→兜底）
4. **记录修订历史**: 每个文件的 `revision_history` 记录每次修改

## Execution

### Step 1: Determine Mode
```
   ├─ 检查输入是否包含 critique_feedback
   │  ├─ 无 → Mode A (Initial Fix)
   │  └─ 有 → Mode B (Revision Fix)
   └─ revision_round = 1 或 (上次 round + 1)
```

### Step 2: Read & Understand
```
🔄 [Phase 6/10] Fix-Agent — 代码修复
   ├─ Fix #1: ServiceResource.java — read file → 33 lines, @Data POJO
   ├─ Fix #2: EsCacheUtil.java — read file → 349 lines, Redis @Component
   └─ ██████░░░░░░░░░░  30%  Files read and understood...
```

### Step 3: Apply Fixes (per file)
For each file:
```
   ├─ ServiceResource.java: ADD @JsonIgnoreProperties above @Data
   │  └─ Edit applied ✅
   ├─ EsCacheUtil.java: REPLACE getTaskLock() with retry + Lua delete
   │  ├─ getTaskLock() → stringRedisTemplate.setIfAbsent + retry ✅
   │  ├─ deleteTaskLock() → Lua script atomic delete ✅
   │  ├─ getLoopNum() → stringRedisTemplate.get + parseInt try/catch ✅
   │  └─ init() → remove setValueSerializer ✅
   └─ ████████████████  100% Done
```

### Step 4: Self-Review
Before returning, verify each fix:
```
   ├─ ServiceResource.java: ✅ annotation present, import added
   ├─ EsCacheUtil.java: ✅ Lua script atomic, StringRedisTemplate used
   ├─ SimDetailServiceImpl.java: ✅ hasText guard before Feign call
   ├─ LeoScmFeignServiceImpl.java: ✅ null check, warn log
   └─ EsSimUpdateTask.java: ✅ try-finally, interrupt handled
```

### Step 5: Revision Check (new)
If in Revision Mode:
```
   ├─ 逐条对照 review 反馈检查是否已修复
   │  ├─ Issue #1: lock 竞态 → ✅ Lua 脚本原子化
   │  └─ Issue #2: 无超时 → ✅ 增加 waitTimeout=3s
   ├─ git diff 确认变更仅涉及反馈指出的文件
   └─ 更新 revision_history
✅ Phase 6 SUCCESS | revision_round: 2 | confidence: 0.85 → 0.92
```

## Fix Confidence per Pattern
| Pattern | Auto-Fix Confidence | Revision Boost | Notes |
|---------|-------------------|----------------|-------|
| Jackson @JsonIgnoreProperties | 0.98 | — | Trivially correct, 通常 1 轮通过 |
| Redis Lua lock | 0.80 → 0.92 | +0.12 | 首轮可能不完整, 修订后提升 |
| Feign null guard | 0.95 | — | 模式简单, 通常 1 轮通过 |
| Schedule lock finally | 0.85 → 0.93 | +0.08 | 多线程边界需修订补齐 |
| Thread safety (L3) | 0.65 → 0.85 | +0.20 | 复杂场景需多轮修订 |
| SQL column fix | 0.70 | — | 可能需要 DBA 确认 |

## Self-Validation
1. ✅ Every analysis.fix has a corresponding file edit?
2. ✅ `git diff --stat` shows expected changes?
3. ✅ No unintended files modified?
4. ✅ Imports added where needed, removed where unused?
5. ✅ Code follows existing conventions (same logger, same patterns)?
6. ✅ (Revision Mode) All critique points addressed?
7. ✅ (Revision Mode) Only changed files referenced in critique?
8. ✅ revision_history updated with round, changes, and delta?
