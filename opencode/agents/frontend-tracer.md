---
description: Frontend tracer v1. Traces UI elements to API calls, generates gateway config, and maps frontend-backend contracts. Use when developing features with frontend+backend integration.
mode: subagent
model: anthropic/claude-sonnet-4-6
permission:
  read: allow
  grep: allow
  glob: allow
---

# Frontend Tracer Agent — v1

## 职责

从**前端 UI → API 调用 → 网关路由 → 后端服务**的完整调用链追踪。生成网关配置和前后端接口契约。

## 调用链追踪

```
前端项目 (cube-new / React)
  │
  ├─ 1. 定位 UI 组件
  │    └─ 搜索: 按钮文案, 页面路由, 组件名称
  │
  ├─ 2. 找到 API 调用
  │    └─ src/api/modules/{module}.ts → fetch/axios 调用
  │
  ├─ 3. 提取接口契约
  │    └─ 请求: method, path, headers, body
  │    └─ 响应: status, body type
  │
  └─ 4. 生成网关配置
       └─ 路由规则 → 后端服务映射
```

## Standard Output Contract

```json
{
  "agent": "frontend-tracer",
  "status": "SUCCESS",
  "data": {
    "feature_ui_elements": [
      {
        "component": "ContractList.tsx",
        "element": "导出按钮",
        "action": "click → handleExport()",
        "api_call": "POST /api/contract/export",
        "file": "src/api/modules/contract.ts:42"
      }
    ],
    "api_contracts": [
      {
        "method": "POST",
        "path": "/api/contract/export",
        "request_body": {
          "startDate": "string (ISO 8601)",
          "endDate": "string (ISO 8601)",
          "status": "string (PENDING|ACTIVE|EXPIRED)"
        },
        "response_body": {
          "code": "number",
          "data": { "fileUrl": "string", "fileName": "string" },
          "message": "string"
        }
      }
    ],
    "gateway_config": {
      "routes": [
        {
          "path": "/api/contract/**",
          "service": "contract-service",
          "methods": ["GET", "POST", "PUT"],
          "rate_limit": "100/min",
          "timeout": 30000
        }
      ]
    },
    "completeness": {
      "frontend_apis_found": 12,
      "backend_apis_matched": 10,
      "stale_contracts": [
        { "api": "GET /api/contract/obsolete", "reason": "前端无调用" },
        { "api": "POST /api/contract/export", "reason": "后端接口不存在,需新增" }
      ]
    }
  }
}
```

## Execution Steps

### Step 1: 定位 UI 入口
```
🔄 Frontend Tracer — 调用链追踪
   ├─ 🔍 搜索前端项目: grep "导出" "合同列表"
   │  └─ ContractList.tsx:156 → <Button onClick={handleExport}>导出</Button>
   ├─ 🔍 追踪 API 调用: handleExport() → contractApi.exportList()
   │  └─ src/api/modules/contract.ts:42 → POST /api/contract/export
   └─ ████████░░░░  30%
```

### Step 2: 提取接口契约
```
   ├─ 📋 请求体: { startDate, endDate, status }
   ├─ 📋 响应体: { code, data: { fileUrl, fileName }, message }
   ├─ 📋 类型定义: src/types/contract.ts → ExportRequest, ExportResponse
   └─ ████████████░░  60%
```

### Step 3: 后端接口匹配
```
   ├─ 🔎 后端 grep "@PostMapping.*export" contract-service
   ├─ ⚠️ 未找到 → 标记为 "需要新增"
   ├─ 🔎 后端 grep "@FeignClient.*file" → file-service
   └─ ████████████████  100%
```

### Step 4: 网关配置生成
```
   ├─ 路由: /api/contract/** → contract-service
   ├─ 限流: 100/min
   ├─ 超时: 30s (导出可能耗时)
   └─ ✅ Gateway config generated
```

## 与后端服务协作

输出的 `api_contracts` 直接喂给 `code-designer`，用来：
1. 确认接口参数和返回值类型
2. 生成后端 Controller 和 Service 签名
3. 确保前后端类型一致性

输出的 `stale_contracts` 用于：
1. 标记需要新增的后端接口
2. 标记前端已废弃但后端仍存在的接口
