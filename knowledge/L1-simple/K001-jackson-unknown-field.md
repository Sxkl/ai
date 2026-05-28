# K001 — Jackson 未知字段反序列化

**级别**: L1 | **裁决**: 3轮 | **置信度**: 0.98

## 匹配特征
```
grep: "Unrecognized field.*not marked as ignorable"
```

## 典型日志
```
ERROR ServiceResourceListHandler : ... convert error, Unrecognized field "soId"
(class net.linksfield.sim.domain.entity.ServiceResource), not marked as ignorable
(10 known properties: ...)
```

## 根因
Jackson `ObjectMapper` 默认 `FAIL_ON_UNKNOWN_PROPERTIES=true`，实体类未包含上游API返回的新字段。

## 修复方案
```java
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
@Data
public class ServiceResource {
    // ...
}
```

## 修复案例
| 日期 | Jira | 文件 | 服务 |
|------|------|------|------|
| 2026-05-15 | PR-6654 | ServiceResource.java | sim-service |
