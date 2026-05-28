# N1 — ES document_missing_exception (upsert替代update)

**级别**: L1 | **裁决**: 3轮 | **置信度**: 0.95

## 匹配特征
```
grep: "document_missing_exception"
或: "update es error" + retry同样update失败
```

## 根因
Kafka consumer 更新 ES 文档时文档尚未被索引(index lag)，`esClient.update()` 对不存在的文档抛 `document_missing_exception`。重试用同样的 update 必然再次失败。

## 修复方案
```java
// 修改前 — update 对不存在文档抛异常
esClient.update(u -> u.index(INDEX).id(id).doc(map).refresh(Refresh.True), ...);

// 修改后 — upsert: 不存在则创建, 存在则更新
esClient.update(u -> u.index(INDEX).id(id).doc(map)
    .docAsUpsert(true).refresh(Refresh.True), ...);
```

## 同时修复
- retry log "retry success" 在 catch 外打印 → 移到真正成功时才打印
- error→warn 降级

## 修复案例
| 日期 | Jira | 文件 | 服务 |
|------|------|------|------|
| 2026-05-15 | PR-6665 | EsServiceImpl.java | cube-server |
