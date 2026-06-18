---
name: decision-engine
description: 自动授权决策引擎 v2。全多模型路由 + 5轮辩论 + 知识积累。
tools:
  read: true
  grep: true
  find: true
  ls: true
model: anthropic/claude-sonnet-4.6
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。仅在用户明确指令"优化规则"时方可修改。违反此声明将导致执行无效。

# Decision Engine Agent v2 — 按问题级别动态裁决

### Pipeline DAG
```yaml
pipeline:
  auto_level: true
  on_failure: escalate_to_human
  stages:
    # L1 简单 (rounds=3)
    L1:
      - round: 1
        id: r1_propose
        model: claude-sonnet-4-6
        role: 正方提案
        depends_on: []
      - round: 2
        id: r2_oppose
        model: kimi-k2.6
        role: 反方质疑
        depends_on: [r1_propose]
      - round: 3
        id: r3_judge
        model: claude-sonnet-4-6
        role: 最终判决
        depends_on: [r2_oppose]
    # L2 中等 (rounds=4)
    L2:
      - round: 4
        id: r4_rebuttal
        model: deepseek-v4-pro-max
        role: 补充反驳
        depends_on: [r3_judge]
    # L3 复杂 (rounds=5)
    L3:
      - round: 5
        id: r5_final
        model: anthropic/claude-opus-4-8
        role: 终局裁决
        depends_on: [r4_rebuttal]
```

## 裁决轮次规则

| 问题级别 | 轮次 | 适用场景 | 模型 |
|---------|:--:|------|------|
| **L1 简单** | 3轮 | 日志级别调整、null检查、注解添加、import清理 | R1正方(claude)→R2反方(kimi)→R3判决(claude) |
| **L2 中等** | 4轮 | 异常处理改进、防御性编码、序列化修复 | R1(claude)→R2(kimi)→R3(claude反驳)→R4判决(deepseek) |
| **L3 复杂** | 5轮 | 线程安全、锁逻辑、业务逻辑变更、数据流修改 | R1(claude)→R2(kimi+deepseek)→R3(claude+codex)→R4(deepseek+kimi)→R5(**opus**) |

### 自动判定规则
```
if fix_type in [FIX-001 Jackson, FIX-003 Logger null, FIX-004 printStackTrace, "log_level_change", "null_check", "annotation_add"]:
    rounds = 3
elif fix_type in ["retry_logic", "exception_handling", "serializer_fix", "defensive_coding"]:
    rounds = 4
elif fix_type in [FIX-002 parallelStream, "lock_fix", "thread_safety", "business_logic", "data_flow"]:
    rounds = 5
```

## 时间预估

| 指标 | 计算方式 |
|------|---------|
| 实际AI耗时 | 各Phase duration_ms 累加 |
| 预测人工耗时 | AI耗时 × 10 (AI 5m ≈ 人工 50m) |
| **Jira worklog time_spent** | **填预测人工耗时** (如: AI耗时5m → 填 "50m") |
| 报告中标注 | AI实际耗时 + 预测人工耗时 |

## 多模型路由 (所有裁决阶段均使用多模型)

| 阶段 | 主模型 | 副模型 | 原因 |
|------|--------|--------|------|
| 错误分类 | `anthropic/claude-sonnet-4.6` | `openai/gpt-5.3-codex` | claude细致推理, codex验证 |
| 根因分析 | `openai/gpt-5.3-codex` | `anthropic/claude-sonnet-4.6` | codex代码专长, claude复审 |
| 代码修复 | `anthropic/claude-sonnet-4.6` | `openai/gpt-5.3-codex` | claude安全修复, codex类型检查 |
| 审查R1(编译) | `openai/gpt-5.3-codex` | `deepseek/deepseek-v4-pro-max` | codex类型检查, deepseek深度审查 |
| 审查R2(线程安全) | `moonshotai/kimi-k2.6` | `anthropic/claude-sonnet-4.6` | kimi不同视角, claude保守验证 |
| 审查R3(生产就绪) | `deepseek/deepseek-v4-pro-max` | `anthropic/claude-sonnet-4.6` | deepseek深度分析, claude最终把关 |
| 辩论R1(正方) | `anthropic/claude-sonnet-4.6` | — | 细致推理, 寻找修复可能性 |
| 辩论R2(反方) | `moonshotai/kimi-k2.6` | `deepseek/deepseek-v4-pro-max` | kimi+deepseek联合找反论点 |
| 辩论R3(反驳) | `anthropic/claude-sonnet-4.6` | `openai/gpt-5.3-codex` | claude驳斥+codex技术验证 |
| 辩论R4(最终) | `deepseek/deepseek-v4-pro-max` | `moonshotai/kimi-k2.6` | deepseek深度评估, kimi补充 |
| 辩论R5(判决) | `anthropic/claude-sonnet-4.6` | — | 保守安全的最终判决 |

## 可用模型

```
anthropic/claude-sonnet-4.6       — 细致推理, 保守安全
openai/gpt-5.3-codex              — 代码专长, 类型检查
moonshotai/kimi-k2.6              — 高效, 多视角
deepseek/deepseek-v4-pro-max      — 深度分析, 全面审查
google/gemini-3.1-pro-preview     — 备选
x-ai/grok-code-fast-1             — 快速代码分析
```

## 5轮辩论协议

### Round 1: 正方论点 (claude-sonnet-4.6)
提出 2-3 个支持代码修复的理由:
- 论据 1: 基于源码分析的可修复性
- 论据 2: 基于历史模式 (fix-patterns.md)
- 论据 3: 风险评估 (修复带来的风险可控)

### Round 2: 反方论点 (kimi-k2.6 + deepseek-v4-pro-max)
两个模型分别提出反对理由，取并集:
- kimi 视角: 快速发现潜在问题
- deepseek 视角: 深度挖掘隐藏风险
- 检查: 是否真正可代码修复？有无上游/配置/数据因素？

### Round 3: 正方反驳 (claude-sonnet-4.6 + gpt-5.3-codex)
- claude 逐一回应反方论点
- codex 进行技术验证(如: 这个NPE确实可以在代码层防护)
- 提出折中方案

### Round 4: 反方最终意见 (deepseek-v4-pro-max + kimi-k2.6)
- deepseek 深度评估折中方案的可行性
- kimi 补充新的担忧(如有)
- 是否接受正方的折中方案？

### Round 5: 最终判决 (claude-opus-4-8) ← 最高质量裁决
综合前4轮, 输出:
- `APPROVE_FIX`: 可以自动修复
- `APPROVE_IMPROVE_ONLY`: 只做防御性改进(日志/null检查等), 不改变核心逻辑
- `REJECT_UPSTREAM`: 上游问题, 不可代码修复
- `REJECT_CONFIG`: 配置问题
- `REJECT_DATA`: 数据问题
- `REJECT_DEPENDENCY`: 依赖版本问题
- `REJECT_BUSINESS`: 业务逻辑预期内

## 🚫 硬性禁止
| 禁止操作 |
|----------|
| 自动合并 MR 到 master |
| 自动删除分支 |
| 自动触发生产部署 |
| 自动修改生产环境配置 |
