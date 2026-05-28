# K005 — 空值null防护

**级别**: L1 | **裁决**: 3轮 | **置信度**: 0.95

## 匹配特征
```
NPE stack trace + 无 null/empty 检查的逻辑
```

## 修复方案
```java
// 修改前
List<X> list = mapper.selectList(ids);
list.parallelStream().forEach(...); // NPE

// 修改后
List<X> list = mapper.selectList(ids);
if (list == null || list.isEmpty()) {
    log.warn("selectList returned empty for ids:{}", ids.size());
    return defaultValue;
}
```

## 修复案例
| 日期 | Jira | 文件 | 服务 |
|------|------|------|------|
| 2026-05-15 | PR-6658 | UpdateContractServiceImpl.java:1694 | iot-contract |
| 2026-05-15 | PR-6663 | BaseOrderImpl.java:294 | iot-order |
