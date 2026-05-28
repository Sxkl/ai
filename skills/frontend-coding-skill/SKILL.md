---
name: "frontend-coding-skill"
description: "前端编码规范模板，覆盖 React/TypeScript、样式、API 与工程约束。"
version: "1.0.0"
author: "linksfield"
---

# Skill: 编码规范

## 技术栈

- React 18 + TypeScript (strict)
- Vite 6 + @tailwindcss/vite
- Tailwind CSS 4 + tw-animate-css
- shadcn/ui (Radix UI + CVA + tailwind-merge)
- react-router 7 (createBrowserRouter)
- react-hook-form
- recharts
- lucide-react 图标
- motion (framer-motion v12)

## TypeScript

1. 严格模式：`strict: true`，`noUnusedLocals`，`noUnusedParameters`
2. 优先用 `interface` 定义 props，复杂联合类型用 `type`
3. 禁止 `any`，必须时用 `unknown` + 类型守卫
4. 组件 props 命名：`{ComponentName}Props`
5. 路径别名：`@/` 指向 `src/`
6. 枚举用 `const enum` 或字面量联合类型，不用 `enum`

## React

1. 函数组件 + hooks，不用 class 组件
2. 组件文件 PascalCase：`OrderDetail.tsx`
3. hook 文件 camelCase：`useOrderForm.ts`
4. 工具函数文件 camelCase：`formatCurrency.ts`
5. 一个文件一个导出组件，辅助子组件可以在同文件但不导出
6. 事件处理函数命名：`handle{Event}`（如 `handleSubmit`）
7. props 回调命名：`on{Event}`（如 `onSubmit`）
8. 避免 inline 对象/函数导致不必要 re-render，用 `useMemo`/`useCallback` 包裹
9. 条件渲染：简单用 `&&`，复杂用提前 return 或抽子组件

## UI 设计规范

**所有 UI 变更必须遵循 `guidelines/Guidelines.md`。**

1. 修改 UI 前先读 `guidelines/Guidelines.md`
2. 颜色、字体、间距、圆角、按钮变体等以 Guidelines 为准
3. 不重复造轮子：先查 `src/app/components/ui/` 是否已有同类组件
4. 不重复造样式：先查 Guidelines 是否已定义对应 token
5. 自定义组件的视觉风格必须与 Guidelines 保持一致

## 样式

1. 优先 Tailwind utility class，不写自定义 CSS
2. 条件 class 用 `cn()` (来自 `@/app/components/ui/utils`)
3. 组件变体用 CVA (`class-variance-authority`)
4. 响应式：mobile-first，断点 `sm:` `md:` `lg:` `xl:`
5. 颜色使用 CSS 变量（已定义在 `styles/index.css`），不硬编码
6. 间距、圆角使用 Tailwind token，保持一致性
7. 动画使用 `motion` 或 Tailwind animate，不用原生 CSS animation

## 文件结构

```
src/
├── main.tsx                    # 入口
├── app/
│   ├── App.tsx                 # 根组件
│   ├── routes.tsx              # 路由表
│   ├── components/
│   │   ├── ui/                 # shadcn 基础组件（不手动修改）
│   │   ├── AdminLayout.tsx     # 布局组件
│   │   ├── AdminSidebar.tsx
│   │   └── ...
│   ├── pages/                  # 页面组件
│   │   ├── Dashboard.tsx
│   │   ├── OrderManagement.tsx
│   │   └── ...
│   ├── hooks/                  # 自定义 hooks（待建）
│   ├── services/               # API 调用层（待建）
│   ├── types/                  # 共享类型定义（待建）
│   └── utils/                  # 工具函数（待建）
├── styles/
│   └── index.css               # Tailwind 入口 + CSS 变量
```

## 命名约定

| 类别 | 格式 | 示例 |
|------|------|------|
| 组件文件 | PascalCase.tsx | `OrderDetail.tsx` |
| hook 文件 | camelCase.ts | `useOrderList.ts` |
| 工具文件 | camelCase.ts | `formatDate.ts` |
| 类型文件 | camelCase.ts | `order.ts` |
| 常量 | UPPER_SNAKE_CASE | `ORDER_STATUS` |
| 组件 | PascalCase | `OrderCard` |
| 函数/变量 | camelCase | `getOrderTotal` |
| CSS 变量 | kebab-case | `--primary-foreground` |

## 导入顺序

1. React / React DOM
2. 第三方库（react-router, recharts, motion...）
3. UI 组件 (`@/app/components/ui/`)
4. 业务组件 (`@/app/components/`)
5. hooks (`@/app/hooks/`)
6. services (`@/app/services/`)
7. types (`@/app/types/`)
8. utils (`@/app/utils/`)
9. 样式（如有）

各组之间空一行。

## API 调用规范

### HTTP 客户端

使用 `ky`（轻量 fetch wrapper）作为统一 HTTP 客户端，禁止裸写 `fetch`。

```bash
npm install ky
```

### 统一实例

在 `src/app/services/http.ts` 中创建全局 ky 实例：

```ts
import ky from 'ky'

export const http = ky.create({
  prefixUrl: import.meta.env.VITE_API_BASE_URL,
  timeout: 30_000,
  hooks: {
    beforeRequest: [
      (request) => {
        const token = localStorage.getItem('token')
        if (token) {
          request.headers.set('Authorization', `Bearer ${token}`)
        }
      },
    ],
    afterResponse: [
      async (_request, _options, response) => {
        if (response.status === 401) {
          localStorage.removeItem('token')
          window.location.href = '/login'
        }
      },
    ],
    beforeError: [
      async (error) => {
        const { response } = error
        if (response) {
          const body = await response.json().catch(() => ({}))
          error.message = body.message || response.statusText
        }
        return error
      },
    ],
  },
})
```

### Service 层结构

每个业务模块一个 service 文件，统一用 `http` 实例：

```ts
// src/app/services/orderService.ts
import { http } from './http'
import type { Order, CreateOrderPayload } from '@/app/types/order'

export const orderService = {
  list: (params?: Record<string, string>) =>
    http.get('orders', { searchParams: params }).json<Order[]>(),

  getById: (id: string) =>
    http.get(`orders/${id}`).json<Order>(),

  create: (payload: CreateOrderPayload) =>
    http.post('orders', { json: payload }).json<Order>(),

  update: (id: string, payload: Partial<CreateOrderPayload>) =>
    http.patch(`orders/${id}`, { json: payload }).json<Order>(),

  delete: (id: string) =>
    http.delete(`orders/${id}`),
}
```

### 拦截器规范

| 拦截器 | 职责 | 位置 |
|--------|------|------|
| `beforeRequest` | 注入 token、添加公共 header、请求日志 | `http.ts` |
| `afterResponse` | 401 跳转登录、403 权限提示、统一错误 toast | `http.ts` |
| `beforeError` | 提取后端错误信息、格式化错误对象 | `http.ts` |
| `beforeRetry` | 重试策略（可选，ky 内置 retry 支持） | `http.ts` |

### 规则

1. **所有 API 调用必须通过 `http` 实例**，禁止 `fetch()` / `axios` / 裸 `ky`
2. **Service 文件不含 UI 逻辑**，只返回数据，错误向上抛
3. **组件中不直接写 URL**，通过 service 方法调用
4. **环境变量**：API 地址通过 `VITE_API_BASE_URL` 配置
5. **类型安全**：所有 `.json<T>()` 调用必须指定泛型
6. **错误处理**：组件层 try-catch + sonner toast，service 层不吞错误
7. **Mock 数据过渡**：POC 阶段 service 可返回 mock 数据，但接口签名保持真实

## 禁止事项

- 不用 `var`，用 `const` 优先，需要重新赋值用 `let`
- 不用 `!important`
- 不用 `index` 作为 list key（除非列表静态不变）
- 不在组件内定义常量/类型，提到文件顶部或单独文件
- 不用 `console.log` 提交到仓库（开发调试后删除）
- 不用 `@ts-ignore`，用 `@ts-expect-error` 并写原因注释
