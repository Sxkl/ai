---
name: "frontend-qa-skill"
description: "前端测试与QA规范模板，覆盖 Vitest 与 Playwright。"
version: "1.0.0"
author: "linksfield"
---

# Skill: QA 规范

## 测试栈

| 层级 | 工具 | 用途 |
|------|------|------|
| E2E | Playwright | 用户流程、跨页面交互、视觉回归 |
| 组件 | Vitest + React Testing Library | 组件渲染、交互、状态 |
| 单元 | Vitest | 工具函数、hooks、纯逻辑 |

## 目录结构

```
src/
├── app/
│   ├── components/
│   │   └── __tests__/          # 组件测试，紧邻源码
│   ├── hooks/
│   │   └── __tests__/
│   ├── utils/
│   │   └── __tests__/
│   └── pages/
│       └── __tests__/
tests/
├── e2e/                        # Playwright E2E 测试
│   ├── orders/
│   │   ├── order-list.spec.ts
│   │   ├── order-create.spec.ts
│   │   └── order-detail.spec.ts
│   ├── dashboard.spec.ts
│   └── auth.spec.ts
├── fixtures/                   # 测试数据
│   └── orders.ts
└── helpers/                    # 测试辅助函数
    └── render.tsx
```

## 文件命名

- 单元/组件测试：`{源文件名}.test.ts(x)`
- E2E 测试：`{功能名}.spec.ts`
- 测试数据：`{领域}.fixtures.ts`

## QA Workflow

```
1. Discover  → 读项目结构，识别测试文件和关键用户流程
2. Run       → 执行 Vitest + Playwright 测试套件
3. Verify    → 手动验证关键流程（headless browser）
4. Record    → 输出 QA-REPORT.md
5. Summary   → 打印通过率和 bug 数
```

QA 过程中**不修改源码**。只记录 bug，修复在开发分支上进行。

## Vitest 组件测试规范

### 基本结构

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { OrderCard } from '../OrderCard'

describe('OrderCard', () => {
  const defaultProps = {
    order: { id: '1', status: 'pending', total: 100 },
    onSelect: vi.fn(),
  }

  it('renders order id and status', () => {
    render(<OrderCard {...defaultProps} />)
    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(screen.getByText('pending')).toBeInTheDocument()
  })

  it('calls onSelect when clicked', async () => {
    render(<OrderCard {...defaultProps} />)
    await fireEvent.click(screen.getByRole('button'))
    expect(defaultProps.onSelect).toHaveBeenCalledWith('1')
  })
})
```

### Vitest 规则

1. 每个 `describe` 对应一个组件或函数
2. `it` 描述行为，不描述实现："renders X" / "calls Y when Z"
3. 用 `screen.getByRole` > `getByText` > `getByTestId`，优先语义查询
4. mock 外部依赖（API、router），不 mock 被测组件内部
5. 测试用户行为，不测内部 state
6. 每个 test 独立，不依赖执行顺序
7. `defaultProps` 定义在 `describe` 顶部，每个 test 可覆盖

### 覆盖要求

| 类型 | 必测 | 可选 |
|------|------|------|
| 页面组件 | 渲染、主要交互、路由跳转 | 边界状态 |
| 业务组件 | props 渲染、事件回调、条件分支 | 动画、样式 |
| UI 组件 | 不测（shadcn 已测） | 自定义变体 |
| hooks | 返回值、状态变更 | 边界条件 |
| utils | 所有分支、边界值 | 性能 |

## Playwright E2E 测试规范

### Locator 优先级（严格顺序）

1. `getByRole('button', { name: 'Submit' })` — 最佳
2. `getByLabel('Email')` — 表单输入
3. `getByText('Welcome')` — 可见文本
4. `getByPlaceholder('Search...')` — placeholder
5. `getByTestId('user-card')` — 显式 test id
6. CSS/XPath — **禁止使用**

### 等待策略

- **禁止** `page.waitForTimeout(ms)` — flaky test 的 #1 原因
- 用 `await expect(locator).toBeVisible()` — 自动重试
- 用 `await page.waitForLoadState('networkidle')`
- 直接调用 action — Playwright 自动等待可交互

### 断言（web-first，自动重试）

```typescript
await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
await expect(page.getByRole('button', { name: 'Save' })).toBeEnabled()
await page.getByRole('button', { name: 'Save' }).click()

await expect(page.getByRole('alert')).toContainText('Saved')
await expect(page).toHaveURL('/dashboard')
```

### Disambiguation

文本可能匹配多个元素时用 `{ exact: true }`：

```typescript
page.getByRole('button', { name: 'Next', exact: true })
```

### 导航 Helper 提取

重复多步导航 → 提取为 helper 函数：

```typescript
async function goToStep(page: Page, step: number) { ... }
```

### Anti-Patterns

| 禁止 | 应该用 |
|------|--------|
| `page.waitForTimeout(2000)` | `expect(locator).toBeVisible()` |
| `page.locator('div.card > button')` | `page.getByRole('button', { name: '...' })` |
| `page.isVisible()` then if/else | `expect(locator).toBeVisible()` |
| `page.$('selector')` | `page.getByRole()` / `page.getByText()` |
| `body.textContent().includes()` | `expect(locator).toContainText()` |
| `.getAttribute('class').includes()` | `toHaveClass()` / `toBeChecked()` |
| Tests sharing state across test() | `beforeEach()` for setup |

### 基本结构

```typescript
test.describe('Order Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/admin/orders')
  })

  test('user can view order list', async ({ page }) => {
    await expect(page.getByRole('table')).toBeVisible()
  })

  test('user can navigate to order detail', async ({ page }) => {
    await page.getByRole('row').nth(1).click()
    await expect(page).toHaveURL(/\/admin\/orders\//)
  })
})
```

### E2E 规则

1. 测试文件按功能模块分目录
2. `beforeEach` 导航到目标页面
3. 测试名描述**用户行为**："user can submit form"，不描述实现
4. 每个 test 独立，可并行运行
5. 网络请求用 `page.route()` mock，不依赖真实 API
6. 截图对比用于视觉回归，存放 `tests/e2e/__screenshots__/`
7. 超时：单个 test 30s，navigation 10s
8. 测试数据不依赖数据库，用 fixture 或 mock

### 页面测试清单

每个页面至少覆盖：

- [ ] 页面加载渲染正确
- [ ] 空状态显示
- [ ] 列表分页/滚动
- [ ] 筛选/搜索
- [ ] CRUD 操作（如适用）
- [ ] 表单验证（如适用）
- [ ] 错误状态处理
- [ ] 响应式布局（mobile / desktop）

## 测试运行

```bash
# 单元 + 组件测试
npx vitest run

# 带覆盖率
npx vitest run --coverage

# E2E 测试
npx playwright test

# E2E JSON 报告
npx playwright test --reporter=json > test-results.json 2>&1

# E2E 带 UI
npx playwright test --ui

# 单个文件
npx vitest run src/app/utils/__tests__/format.test.ts
npx playwright test tests/e2e/orders/order-list.spec.ts
```

## QA-REPORT.md 模板

```markdown
# QA Report
**Project**: @sphere2/app
**Date**: {date}
**Tester**: Claude Code (agent/pam-fs)
**Branch**: {branch}
**Commit**: {short sha}

## Summary
| Metric          | Value    |
|-----------------|----------|
| Tests Run       | n        |
| Passed          | n (n%)   |
| Failed          | n (n%)   |
| Skipped         | n        |
| Critical Bugs   | n        |
| High Bugs       | n        |
| Medium Bugs     | n        |
| Low Bugs        | n        |

## Test Results
| Test | Status | Duration | Error |
|------|--------|----------|-------|
| ... | PASS/FAIL | 1.2s | error message if failed |

## Bugs Found

### [BUG-001] {Title}
**Severity**: CRITICAL / HIGH / MEDIUM / LOW
**Category**: Auth / UI / Data / Performance / UX
**Page/Route**: `/path`
**Steps to Reproduce**:
1. Go to ...
2. Click ...
3. Observe ...
**Expected**: What should happen
**Actual**: What actually happens
**Evidence**: Error message, screenshot path, or console output

## Test Coverage Gaps
- [ ] Flows not covered by existing tests

## Recommendations
- Priority fixes (CRITICAL/HIGH bugs)
- Test improvements needed
```

## CI 集成要求

1. MR 必须通过所有测试才能合并
2. 组件/单元测试覆盖率目标：核心业务逻辑 > 80%
3. E2E 覆盖所有关键用户流程
4. 新功能必须附带测试，bug fix 必须附带回归测试
