# K007 — REST响应null检查

**级别**: L2 | **裁决**: 4轮 | **置信度**: 0.85

## 匹配特征
```
restTemplate.postForObject / .getForObject 返回后直接 .getXxx()
```

## 根因
`restTemplate.postForObject()` 可能在网络异常时返回 null。

## 修复方案
```java
// 修改前
BbcResponse response = restTemplate.postForObject(url, entity, BbcResponse.class);
if("S".equals(response.getOperateCode())){ // 可能NPE

// 修改后
BbcResponse response = restTemplate.postForObject(url, entity, BbcResponse.class);
if (response == null) {
    log.error("调用BBC返回null, type={}, assetId={}", type, assetId);
    return;
}
if("S".equals(response.getOperateCode())){
```

## 修复案例
| 日期 | Jira | 文件 | 服务 |
|------|------|------|------|
| 2026-05-15 | PR-6662 | CreateOrReNewCallbackEventHandler.java:92 | iot-order |
