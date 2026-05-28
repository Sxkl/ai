---
name: prd-to-verified
description: PRD→验证通过 标准开发DAG。13层流水线从需求采集到知识沉淀全自动化，实时进度追踪，质量门禁把关。借鉴Stargate SkillOrchestrator架构。Use ONLY when starting standardized fullstack development. Trigger keywords: PRD开发、标准流程、从PRD开始、全流程DAG、prd-to-verified
---

# PRD → Verified — 标准开发 DAG

借鉴 [Stargate](https://stargate.lf.emmc.cc) 的 SkillOrchestrator 架构：
- JSON DAG 定义 (`skill-dag.json`)
- 拓扑排序 + 逐层并行执行
- 实时进度追踪 (每步状态可见)
- 质量门禁 + 反馈循环

## 流水线总览

```
① AI Chat ──→ ② Brewer ──→ ③ Distiller/Arch/KB ──→ ④ FE/BE Trace
                                                          ↓
⑬ Nebula/Verify ←── ⑫ Git/Jira ←── ⑪ Quality ←── ⑩ Crossfire
                                                    ↑
                          ⑦ Taster ←── ⑥ Design Review ←── ⑤ Code Designer
                              ↓
                          ⑧ Data/API/Biz/FE ──→ ⑨ Lint/Type/Test
```

## 13 层进度展示

每一层执行时实时输出进度条：
```
████████████░░░░░░░░░░░░░░  62%  (Layer 7/13)
✅ L0 AI Chat     [120s]
✅ L1 Brewer      [60s]
🔄 L7 Data Layer  [RUNNING]
⏳ L7 API Layer   [QUEUED]
```

## 使用方式

```
PR-6312
```

或直接描述需求即可自动触发全流程。
