# K004 — 正常业务态 error 降级 warn

**级别**: L1 | **裁决**: 3轮 | **置信度**: 0.99

## 匹配特征
```
订单已结束/操作不允许/权限不足等正常业务逻辑 → ERROR日志
```

## 根因
开发者习惯性使用 `log.error`，但某些场景是正常业务状态。

## 修复方案
```java
// 修改前
log.error("orderId={}已经结束 不需要再处理周期切换", orderId);

// 修改后
log.warn("orderId={}已经结束 不需要再处理周期切换", orderId);
```

## 判断标准
- ORDERFINISH/已结束/已完成等终态 → WARN
- 权限/校验不通过 → WARN
- 上游返回预期的失败码 → WARN
- 真正的系统异常/崩溃 → 保持 ERROR

## 修复案例
| 日期 | Jira | 文件 | 服务 |
|------|------|------|------|
| 2026-05-15 | PR-6663 | ProcessCycleSwitchRequest.java:302 | iot-order |
| 2026-05-15 | PR-6663 | BaseOrderImpl.java:282,290 | iot-order |
