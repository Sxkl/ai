# Prompt Caching Guide — Claude 成本优化

## 原理

Claude API 自动缓存重复的前缀内容（system prompt + tool definitions），后续请求跳过重复计算，**降低成本 ~60%**。

```
请求 1: [System Prompt 4K tokens] + [User Msg] → 全量计算
请求 2: [System Prompt 同上]     + [User Msg] → 前 4K 命中缓存 ✨
请求 3: [System Prompt 同上]     + [User Msg] → 前 4K 命中缓存 ✨
```

## 当前集群缓存命中率预估

你已有 41 个 Agent，全部使用 `claude-sonnet-4-6`。缓存收益：

| Agent 类型 | 缓存命中 | 预估节省 |
|-----------|:--:|:--:|
| analyze-agent | system prompt + 工具定义 | 40-50% |
| fix-agent | system prompt + 审查规则 | 35-45% |
| review-agent | P0-P2 审查项 (305行) | 50-60% |
| 其他高频 agent | 固定 prompt 前缀 | 30-40% |

**综合预估：每月 token 成本降低 40-55%**

## 确保缓存命中的规则

1. **System prompt 不变化** — 不在对话中间改 agent 指令
2. **工具定义不变化** — 不在 session 中间开关工具
3. **用户消息放最后** — 变化的部分只在末尾

## 验证方法

```bash
# 查看 API 响应中的 cache 指标
# 响应头: anthropic-* 字段显示 cache_read_input_tokens / cache_creation_input_tokens
```

## 不需要改任何代码

Claude API 从 2024 年起默认启用 prompt caching。你当前的 Agent 配置已经自然受益——只要保持 system prompt 稳定即可。
