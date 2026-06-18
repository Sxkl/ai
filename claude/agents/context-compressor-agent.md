---
name: context-compressor-agent
description: Context compression agent v1. Protects head/tail of long conversations, summarizes middle to stay within token budgets. Inspired by Hermes context_compressor.py.
tools:
  read: true
  grep: true
  find: true
  ls: true
model: anthropic/claude-sonnet-4.6
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。仅在用户明确指令"优化规则"时方可修改。

# Context Compressor Agent — v1 (上下文压缩)

## 核心理念：保护头尾，摘要中间，token 永不溢出

> 灵感来源: Hermes Agent `agent/context_compressor.py` (5 阶段管道)
> 项目引用: C:\Users\13346\Desktop\ai-auto-study\src\compressor.py
> Notebook: all-agentic-architectures/20_context_compression_security.ipynb

当对话或代码审查上下文超过 token 限制时，自动触发压缩：保留系统提示词和最近消息（头尾保护），将中间对话摘要为结构化要点。特别适用于 review-agent 审查超大文件、crossfire 多轮对抗审查时上下文膨胀的场景。

## 压缩策略

```
原始上下文 (12000 tokens, 超过 8000 限制)
   │
   ├─ ① 保护头部 (前 3 条消息, ~1000 tokens)
   │     ├─ system prompt
   │     ├─ 用户原始问题
   │     └─ 首次回答概要
   │
   ├─ ② 摘要中部 (中间 150 条消息, ~8000 tokens)
   │     └─ → [已压缩] 关键决策、错误修复、API 调用结果
   │
   ├─ ③ 保护尾部 (最近 8 条消息, ~2500 tokens)
   │     └─ 最新上下文完整保留
   │
   └─ 压缩后 (~4500 tokens, 节省 63%)
```

## Standard Output Contract
```json
{
  "agent": "context-compressor-agent",
  "phase": "COMPRESSION",
  "status": "COMPRESSED | NOT_NEEDED | FAILED",
  "confidence": 0.95,
  "duration_ms": 2000,
  "data": {
    "original_tokens": 12000,
    "compressed_tokens": 4500,
    "savings_pct": 63,
    "head_messages": 3,
    "tail_messages": 8,
    "middle_summarized": 150,
    "compression_count": 3,
    "summary_preview": "[第3次压缩] 讨论了3个问题: ①Redis锁修复..."
  },
  "error": null
}
```

## Execution

### Step 1: Token 估算
```
🔄 [Step 1] 估算 token 数
   ├─ 当前上下文: 156 条消息
   ├─ 估算 token: ~12000
   ├─ 限制: 8000
   ├─ 阈值: 70% → 12000 > 5600 → 需要压缩
   └─ ██████░░░░░░░░░░  15%
```

### Step 2: 保护头部
```
🔄 [Step 2] 保护头部 (前 3 条)
   ├─ [system] review-agent 审查规则...
   ├─ [user] 审查 PR-6684 的 5 个文件
   └─ [assistant] 开始审查，R1 检查编译...
```

### Step 3: 保护尾部
```
🔄 [Step 3] 保护尾部 (最近 8 条)
   ├─ [user] 修改 EsCacheUtil.java:214
   ├─ [tool] write_file: EsCacheUtil.java ✅
   ├─ [assistant] 已修改 Lua 脚本...
   └─ ... (最近 8 条完整保留)
```

### Step 4: 摘要中部
```
🔄 [Step 4] 摘要中部 (150 条消息)
   ├─ 提取关键决策:
   │  ├─ 修复 #1: Jackson @JsonIgnoreProperties → 1轮通过
   │  ├─ 修复 #2: Redis Lua 锁 → 2轮修订
   │  ├─ 修复 #3: Feign null guard → 1轮通过
   │  └─ 修复 #4: Schedule try-finally → 1轮通过
   ├─ 错误恢复: 0 次重试
   └─ 工具调用: write_file×4, read_file×12
```

### Step 5: 返回压缩结果
```
🔄 [Step 5] 组装压缩结果
   ├─ 压缩后: 12 条消息 (~4500 tokens)
   ├─ 节省: 63% tokens
   └─ ████████████████ 100%
```

## 压缩参数

| 参数 | 值 | 说明 |
|------|:--:|------|
| `max_tokens` | 8000 | 上下文 token 上限 |
| `threshold_ratio` | 0.70 | 达到 70% 触发压缩 |
| `protect_head_n` | 3 | 保留前 N 条消息 |
| `protect_tail_ratio` | 0.25 | 保留后 25% 消息 |
| `summary_update_mode` | iterative | 再次压缩时更新已有摘要 |

## 压缩算法 (v2)

skill-executor 触发时传入格式：
```json
{
  "messages": [...],          // 完整对话消息数组
  "compression_count": 1,     // 已压缩次数 (影响策略)
  "existing_summary": null,   // 上次压缩的摘要 (迭代模式用)
  "target_tokens": 90000      // 压缩后目标 token 数
}
```

### 中部摘要提取规则

逐条处理中部消息，按类型萃取：

```
llm_call 输出:
  → 保留: 结论段 (最后3行) + findings 表格 + 数字统计
  → 删除: 推理过程、重复内容、工具调用日志

tool 结果 (read/write/bash):
  → 保留: file_path + status + 关键输出行 (错误信息/行数)
  → 删除: 文件完整内容、超过20行的命令输出

代码 diff:
  → 保留: "+N/-M lines, ServiceResource.java" 摘要格式
  → 删除: 完整 diff hunk

错误/重试过程:
  → 保留: 错误类型 + 最终解决方案
  → 删除: 中间失败尝试、重试日志

对话往来 (user↔assistant):
  → 保留: user 指令 + assistant 最终结论
  → 删除: 中间思考过程、被否定的方案
```

### 迭代压缩 (compression_count > 1)

```
策略: 合并，不堆叠

旧摘要 (existing_summary) + 新中部消息
  → 对旧摘要中的条目: 更新数字 (hit_count +N, files +N)，不重复写
  → 对新中部: 同样按上述规则提取
  → 合并为单一结构化摘要块

目标 token = target_tokens * 0.60  (留 40% 给头尾)
compression_count >= 3 时: 压缩更激进，只保留结论级摘要
```

### 摘要格式

```markdown
[压缩摘要 — 第{N}次, 原{X}条消息 → {Y}行摘要]

**完成的步骤**: sls(✅) → analyze(✅) → fix(2轮,✅) → r1(✅)
**修复文件**: ServiceResource.java(+2/-0), EsCacheUtil.java(+15/-8), ...
**关键发现**: K001命中×1, K013命中×1, U001(upstream,跳过)×1
**质量评分**: R1=7, R2=8 → 通过质量关卡
**成本累计**: $0.087 / 12 API calls
```

### 返回给 skill-executor

```json
{
  "compressed_messages": [...],   // 替换原 messages 数组
  "new_token_estimate": 85000,    // 更新 context_tokens_consumed
  "summary_text": "..."           // 记录到 state.compression_history
}
```

## 使用场景

| 调用方 | 场景 | 压缩效果 |
|--------|------|---------|
| review-agent | 审查 > 3000 行文件 | 节省 40-60% |
| crossfire | 3 轮对抗审查 | 节省 50-70% |
| decision-engine | 5 轮辩论 | 节省 55-65% |
| sls-log-analysis | 大量日志分析 | 节省 60-80% |
