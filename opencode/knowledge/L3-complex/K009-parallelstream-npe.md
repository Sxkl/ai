# K009 — parallelStream NPE

**级别**: L3 | **裁决**: 5轮 | **置信度**: 0.90

## 匹配特征
```
NullPointerException in ForkJoinTask + .parallelStream() 调用
```

## 根因
对 null 集合调用 `.parallelStream()` 通过 ForkJoinTask 传播 NPE。

## 修复方案
```java
// 修改前
List<X> list = mapper.selectList(ids);
list.parallelStream().forEach(...); // NPE in ForkJoinTask

// 修改后
List<X> list = mapper.selectList(ids);
if (list == null || list.isEmpty()) {
    log.warn("list is empty, skip processing");
    return;
}
list.parallelStream().forEach(...);
```

## 注意
- ForkJoinTask 中的 NPE 堆栈信息会被包装，需要追溯原始调用
- 不建议用 `Optional.ofNullable()` 替代 null check (性能开销)

## 修复案例
| 日期 | Jira | 文件 | 服务 |
|------|------|------|------|
| 2026-05-15 | PR-6658 | UpdateContractServiceImpl.java:1694 | iot-contract |
