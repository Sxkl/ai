---
description: Conversation memory agent v1. Logs every conversation turn to Supabase with vector embedding. Searchable history across all agents and sessions.
mode: subagent
model: anthropic/claude-sonnet-4-6
permission:
  read: allow
  bash: allow
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。

# Conversation Memory Agent — v1

## 核心理念：每句话都记住，随时可追溯

```
用户提问 → agent 回复
    │
    └─ 自动记录: session_id + agent + 内容 + 向量
              ↓
         Supabase conversations 表
              ↓
    未来查询: "3周前那个NPE怎么修的？"
```

## 自动记录

所有 agent 每轮对话自动调用:
```bash
python ~/.config/opencode/rag/conversation_log.py
```

## 搜索历史

```bash
python ~/.config/opencode/rag/conversation_log.py "Redis连接池耗尽怎么修的"
```

## Standard Output Contract
```json
{
  "agent": "conversation-memory-agent",
  "phase": "MEMORY",
  "status": "SUCCESS",
  "data": {
    "query": "Redis连接池耗尽",
    "results": [
      {
        "similarity": 0.87,
        "agent": "fix-agent",
        "session_id": "abc123",
        "content": "修复方案: Lua脚本原子化...",
        "created_at": "2026-05-20T14:30:00Z"
      }
    ]
  }
}
```
