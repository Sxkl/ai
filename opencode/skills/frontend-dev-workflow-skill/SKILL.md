---
name: "frontend-dev-workflow-skill"
description: "前端开发工作流模板，约束分支、提交流程与质量门禁。"
version: "1.0.0"
author: "linksfield"
---

# Skill: 开发流程

## 分支策略

```
master          ← 生产分支，仅通过 PR 合并
  └── develop   ← 开发主干，所有功能分支的基准
       ├── agent/pam-fs       ← Pam 工程 agent 分支
       ├── agent/moji         ← Moji 产品 agent 分支
       ├── feat/xxx           ← 功能分支
       ├── fix/xxx            ← 修复分支
       └── refactor/xxx       ← 重构分支
```

## 分支命名

| 类型 | 格式 | 示例 |
|------|------|------|
| 功能 | `feat/{模块}-{描述}` | `feat/order-refund` |
| 修复 | `fix/{模块}-{描述}` | `fix/order-status-display` |
| 重构 | `refactor/{模块}-{描述}` | `refactor/order-crud` |
| Agent | `agent/{agent名}` | `agent/pam-fs` |

## 开发循环（严格遵守）

```
1. Plan    → 列出实现步骤，等待确认
2. Implement → 一次只改一个小功能
3. Build   → npm run build，必须通过
4. Test    → 写测试 + 跑测试，必须全绿
5. Commit  → 原子提交，描述性消息
6. Summary → 2-3 句总结
```

每个循环只做一个逻辑变更。Build 或 test 失败时原地修复，不跳过。

## Commit 规范

格式：`{type}: {description}`

| type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `refactor` | 重构（不改变行为） |
| `style` | 样式调整（不影响逻辑） |
| `docs` | 文档变更 |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖 |

规则：
1. 全小写，不加句号
2. 描述写"做了什么"而非"改了什么文件"
3. 一个 commit 一个逻辑变更
4. 不提交 `console.log`、`.env`、`node_modules`
5. Agent commit 附带 `Co-Authored-By` 标记

## PR 流程

1. 从 `develop` 创建功能分支
2. 开发完成，自测通过
3. `git push -u origin {branch}`
4. 创建 PR → `develop`
5. 填写 PR 模板（Summary + Test Plan）
6. 通过 code review
7. Squash merge 到 develop
8. 删除功能分支

## 代码变更前检查

每次修改代码前：

1. `git pull origin develop` 保持最新
2. 确认在正确分支上
3. UI 变更前先读 `docs/design.md`（如存在）
4. 涉及新模块时先读对应 `docs/req-*.md`

## 环境

| 环境 | 分支 | 构建命令 |
|------|------|---------|
| 开发 | `develop` | `npm run dev` |
| UAT | `develop` | `npm run build:uat` |
| 生产 | `master` | `npm run build` |

## 端口规则

- 默认 dev server: 5173
- 端口被占用时用下一个可用端口，**不杀已有进程**
- Playwright 测试用独立端口

## 依赖管理

1. 新增依赖前确认是否已有等价包
2. 优先用已有生态（Radix > 新引入其他 UI 库）
3. `npm install` 后检查 `package-lock.json` 变更是否合理
4. devDependencies 和 dependencies 分清
