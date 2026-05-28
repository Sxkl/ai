# K003 — e.printStackTrace() 

**级别**: L1 | **裁决**: 3轮 | **置信度**: 0.98

## 匹配特征
```
grep: "e\.printStackTrace\(\)"
```

## 根因
`e.printStackTrace()` 输出到 stderr，不被日志聚合系统采集。

## 修复方案
```java
// 修改前
} catch (Exception e) {
    log.error("error:{}", e.getMessage());
    e.printStackTrace();
}

// 修改后
} catch (Exception e) {
    log.error("operation failed, key:{}", key, e);
}
```

## 修复案例
| 日期 | Jira | 文件 | 服务 |
|------|------|------|------|
| 2026-05-15 | PR-6649 | MnoGatewayCommonListener.java | contract-service |
