---
name: continuous-loop
description: Continuous Loop 8阶段开发循环。AI Chat→Brewer→Distiller→Taster→GitLab→Crossfire→Destroyer→Nebula↻。全自动化开发流水线，每阶段产出喂给下一阶段，知识沉淀反哺下一轮。Use ONLY when starting a new feature development from scratch. Trigger keywords: 新功能开发、从零开始、Continuous Loop、8阶段、开发循环
---

# Continuous Loop — 8 阶段开发循环

## 循环全景

```
① AI Chat ──→ ② Brewer ──→ ③ Distiller ──→ ④ Taster
  需求采集       PRD生成      需求提取        测试计划
                                                  ↓
⑧ Nebula ←── ⑦ Destroyer ←── ⑥ Crossfire ←── ⑤ GitLab
  知识沉淀      缺陷分析        交叉验证        开发实现
   ↓
   └──→ 反哺 ① AI Chat (下一次循环更聪明)
```

## 各阶段说明

| # | Agent | 输入 | 输出 |
|:-:|-------|------|------|
| ① | ai-chat | 用户初始描述 / nebula 反馈 | 需求原料 (Requirement Raw) |
| ② | brewer | 需求原料 | 结构化 PRD (AC + 约束 + 风险) |
| ③ | distiller | PRD | 技术规格 (API/实体/模块/约束) |
| ④ | taster | 技术规格 | 测试合约 (TDD 测试用例) |
| ⑤ | gitlab-dev | 技术规格 + 测试合约 | 实现代码 (测试全部通过) |
| ⑥ | crossfire | 实现代码 + PRD | 3轮验证结果 (PRD/架构/生产) |
| ⑦ | destroyer | 验证缺陷 | 根因分析 + 修复方案 + 预防规则 |
| ⑧ | nebula | 全部产出 | 知识沉淀 + 反哺 AI Chat |

## 使用方式

```
# 触发 Continuous Loop
开发一个新功能：用户需要导出合同列表为 Excel

# 或指定更详细的需求
用 Continuous Loop 开发：用户可以在合同列表页按时间和状态筛选，
导出为 Excel 文件，单次上限 10000 条
```

## 特色

- **测试先行**: Taster 先写测试，GitLab 必须通过测试
- **交叉验证**: Crossfire 从 PRD/架构/生产 3 个角度审查
- **知识沉淀**: Nebula 自动学习，下次开发更快更准
- **闭环进化**: 每轮循环产出沉淀知识，反哺下一轮
