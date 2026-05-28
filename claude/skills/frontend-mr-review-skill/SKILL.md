---
name: "frontend-mr-review-skill"
description: "前端 MR 评审与提交流程模板，覆盖质量门禁、测试与提交流程。"
version: "1.0.0"
author: "linksfield"
---

# Skill: MR Review 规范

## GitLab 配置

- Host: `git.io.linksfield.net`
- Project: `sphere/frontend-sphere2-poc`
- API: `https://git.io.linksfield.net/api/v4`
- Token: 优先使用环境变量 `GITLAB_TOKEN`，不依赖 remote URL
- MR 即 PR（GitLab 称 Merge Request）

## 提交 MR 前自动流程

当 agent 准备提交 MR 时，**必须按以下步骤顺序执行**：

### Step 1: 检测源分支冲突

```bash
CURRENT=$(git branch --show-current)
git fetch origin develop
git merge-tree $(git merge-base HEAD origin/develop) HEAD origin/develop
```

判断逻辑：
- **无冲突** → 继续 Step 2
- **有冲突** → 提示用户：

```
⚠️ 当前分支与 develop 存在冲突文件：
  - src/app/pages/OrderManagement.tsx
  - src/app/routes.tsx

建议：
1. git fetch origin develop
2. git rebase origin/develop
3. 解决冲突后 git rebase --continue
4. 再提交 MR

是否现在执行 rebase？
```

用户确认后执行 rebase，解决冲突，再继续。

### Step 2: Quality Gates（自动检查）

Review 完整 diff（所有 commit，不只是最新的）。

```bash
BASE=$(git merge-base HEAD origin/develop)
```

**Gate 1: Clean Working Tree**
```bash
git status --porcelain
```
有未提交的变更 → 提示用户先 commit 或 stash。

**Gate 2: Debug 残留**
```bash
git diff origin/develop...HEAD | grep -n "console\.log\|debugger\|TODO.*HACK\|_old\|_backup"
```

**Gate 3: Type Safety**
```bash
git diff origin/develop...HEAD -- '*.ts' '*.tsx' | grep -n ": any\|as any\|@ts-ignore"
```

**Gate 4: Security**
- 硬编码密钥、token、密码
- `.env` 文件泄漏
- `dangerouslySetInnerHTML` 无 sanitize
- API 路由无 auth 中间件

**Gate 5: API Client 合规**
- 禁止裸 `fetch()`，必须用 `http` 实例（参考 `frontend-coding-skill.md`）
- 无重复 auth/header 逻辑

**Gate 6: 项目规范合规**
- 符合 `frontend-coding-skill.md` 约定
- UI 变更符合 `design.md`（如存在）
- shadcn UI 组件未被手动修改

每个 Gate 输出 ✅ / ❌ + 详情。

### Step 3: Code Review

**Review 维度：**

| 维度 | 关注点 |
|------|--------|
| 正确性 | 逻辑错误、off-by-one、null/undefined、缺少 await |
| AI Anti-Patterns | 重复组件（已有类似的）、copy-paste 逻辑该提取为 hook/util、业务逻辑放在 UI 组件里 |
| 架构 | 新文件与已有模块职责重复、缺少抽象层 |
| 性能 | N+1 查询、无分页、大对象在 state 导致 re-render |
| 可观测性 | 新 error path 无日志、catch 吞错误 |

**Confidence 评分**（0-100）：
- 0-25: 误报或吹毛求疵
- 25-50: 可能有问题，需要验证
- 50-75: 很可能有问题，值得修
- 75-100: 确认有问题，必须修

只报告 **≥ 50** 的 finding。

### Step 4: 强制测试报告

**不能空口说"测试通过"。** 必须运行并输出结构化报告：

```bash
npx vitest run --reporter=json 2>&1
npx playwright test --reporter=json 2>&1
```

输出格式：

```markdown
## Test Results
| Test File | Pass | Fail | Total |
|-----------|------|------|-------|
| ... | n | n | n |

## Coverage Analysis
| PR 中变更的功能 | 有测试? | 测试用例 |
|----------------|---------|---------|
| 新增订单退款 | ✅ | order › refund flow |
| 新增 API /refund | ❌ | 未覆盖 |
```

### Step 5: 查找现有 MR

```bash
if [ -z "$GITLAB_TOKEN" ]; then
  echo "GITLAB_TOKEN is required"
  exit 1
fi
TOKEN="$GITLAB_TOKEN"
API="https://git.io.linksfield.net/api/v4"
PROJECT="sphere%2Ffrontend-sphere2-poc"

curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "$API/projects/$PROJECT/merge_requests?source_branch=$CURRENT&state=opened"
```

### Step 6: 决策 + 提交

```
有 open MR？
├── YES → git push → MR 自动更新 → 输出 MR URL
└── NO  → git push -u → 创建新 MR → 输出 MR URL
```

创建 MR：

```bash
curl -s -X POST -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  "$API/projects/$PROJECT/merge_requests" \
  -d '{
    "source_branch": "'$CURRENT'",
    "target_branch": "develop",
    "title": "feat: 描述",
    "description": "...",
    "squash": true,
    "remove_source_branch": true
  }'
```

追加到现有 MR：

```bash
git push origin $CURRENT
# 可选：添加评论
curl -s -X POST -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  "$API/projects/$PROJECT/merge_requests/$MR_IID/notes" \
  -d '{"body": "追加 commit: xxx"}'
```

## 完整决策流程图

```
agent 准备提 MR
    │
    ▼
[1] git fetch origin develop
    │
    ▼
[2] 检测 merge conflict ──── 有冲突 ──→ 提示 rebase ──→ 用户确认 ──→ rebase
    │                                                                    │
    │ 无冲突                                                             │
    ▼                                                                    ▼
[3] Quality Gates (6 gates) ──── 任一 ❌ ──→ 报告问题，询问是否继续
    │
    │ 全 ✅
    ▼
[4] Code Review (confidence ≥ 50 的 findings)
    │
    ▼
[5] 强制测试报告
    │
    ▼
[6] 查 open MR (source=当前分支)
    │
    ├── 找到 open MR ──→ git push ──→ MR 自动更新 ──→ 输出 MR URL
    │
    └── 未找到 ──→ git push -u ──→ 创建新 MR ──→ 输出 MR URL
```

---

## MR-REPORT.md 输出

每次 review 输出结构化报告：

```markdown
# MR Report
**Branch**: {branch}
**Base**: develop
**Date**: {date}
**Reviewer**: Claude Code (agent/pam-fs)
**Files Changed**: {n}
**Lines**: +{added} -{removed}

## Verdict: READY ✅ / NOT READY ❌

## Gate Results
| Gate | Status | Details |
|------|--------|---------|
| Clean tree | ✅/❌ | ... |
| Debug residue | ✅/❌ | ... |
| Type safety | ✅/❌ | ... |
| Security | ✅/❌ | ... |
| API client | ✅/❌ | ... |
| Project standards | ✅/❌ | ... |

## Code Review Findings

### [blocker] {Title} (confidence: {n}/100)
**File**: `path/to/file.ts:42`
**Category**: Bug / Security / AI-AntiPattern / Architecture / Performance
**Evidence**:
{diff showing the issue}

## What Looks Good
- {Positive observations}

## Test Report
{Structured test report}

## MR Description (copy-paste ready)
{Generated description}
```

---

## Review 评论规范

### 标记

| 前缀 | 含义 | 是否阻塞 |
|------|------|---------|
| `[blocker]` | 必须修改才能合并 | ✅ |
| `[suggestion]` | 建议修改，不强制 | ❌ |
| `[question]` | 需要作者解释 | ❌ |
| `[nit]` | 格式/命名等小问题 | ❌ |
| `[praise]` | 写得好的地方 | ❌ |

### 评论格式

```
[blocker] OrderCard: `any` type on line 23

应该用 `OrderStatus` 类型替代。参考 `frontend-coding-skill.md` 禁止 any 规则。

建议：
- const status: OrderStatus = order.status
+ const status = order.status as OrderStatus
```

---

## MR 描述模板

```markdown
## Summary
- 简要描述做了什么（1-3 bullet points）

## Changes
- 列出主要变更文件和原因

## Test Results
{N pass, N fail}

## Checklist
- [ ] build 通过
- [ ] 无 console.log / debug 代码
- [ ] 无 any 类型引入
- [ ] API 调用使用 http 实例
- [ ] 项目规范合规
- [ ] 测试覆盖

## Screenshots
（UI 变更时附截图，标注前后对比）

## Related
- 关联需求：`docs/req-xxx.md`
```

## 合并策略

1. MR 至少 1 人 approve 才能合并
2. 合并后自动删除源分支（`remove_source_branch: true`）
3. 合并方式根据 commit 内容决定：

| 场景 | 合并方式 | 设置 |
|------|---------|------|
| 全部同类型 commit（如都是 `feat:` 或 `docs:`） | **Squash Merge** | `"squash": true` |
| 不同类型 commit（`feat:` + `fix:` + `refactor:`） | **Merge Commit** 或 **Rebase Merge** | `"squash": false` |
| 单个 commit | **Merge Commit** | `"squash": false` |
| 混乱 commit（"wip"、"fix typo"、"aaaa"） | **Squash Merge** | `"squash": true` |

4. Squash 时 MR 标题即为 commit message，遵循 commit 规范
5. 非 squash 时确保每个 commit 都符合 commit 规范（`type: description`）

## 自动化检查（CI）

MR 提交后自动运行：

1. `npm run build` — 构建检查
2. `npx vitest run` — 单元/组件测试
3. `npx playwright test` — E2E 测试（如已配置）
4. TypeScript 类型检查

任一失败则阻塞合并。
