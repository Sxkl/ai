# K002 — Logger e.getMessage() null

**级别**: L1 | **裁决**: 3轮 | **置信度**: 0.95

## 匹配特征
```
grep: "log\.error.*e\.getMessage()"
日志输出: "consume exception:null"
```

## 根因
`e.getMessage()` 返回 null，日志中占位符被填充为 "null"。

## 修复方案
```java
// 修改前
log.error("consume exception:{}, message:{}", e.getMessage(), JsonUtils.toJson(message));
e.printStackTrace();

// 修改后
log.error("consume failed, tag:{}, msgId:{}", tag, msgId, e);
// e.printStackTrace() 移除 — SLF4J参数化自动包含完整堆栈
```

## 注意
- 提取变量到外层作用域以便catch块访问
- 移除 `e.printStackTrace()` 
- 用异常对象本身作为最后参数 (SLF4J会自动打印堆栈)

## 修复案例
| 日期 | Jira | 文件 | 服务 |
|------|------|------|------|
| 2026-05-15 | PR-6649 | MnoGatewayCommonListener.java | contract-service |
