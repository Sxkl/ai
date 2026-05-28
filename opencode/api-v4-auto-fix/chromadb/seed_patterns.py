"""
向量化写入全部 8 个已确认问题模式到 ChromaDB + 22下游服务扫描结果
基于 PR-6836 全链路分析
"""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from init_db import init_chromadb

PATTERNS = [
    {
        "id": "K001",
        "doc": "MNO Gateway Read timed out through sim-service. Error: Sphere2SimApiSupportFeignClient#querySimDetail SocketTimeoutException latency=30030ms. Chain: cube-api-v4 → enterprise-gateway → sim-service → MNO Gateway /biz/operation",
        "meta": {
            "error_type": "下游超时-MNO",
            "severity": "P0", 
            "service": "sim-service",
            "fix": "MNO独立10s超时 + CompletableFuture.orTimeout()",
            "count_2months": 19000,
            "code": "SimApiServiceImpl.java:1962 asyncInvokeLastSession"
        }
    },
    {
        "id": "K002",
        "doc": "MNO Gateway Read timed out through cube-server. Error: ApiCubeFeignClient#statusToDetail/details SocketTimeoutException latency=30030ms. Chain: cube-api-v4 → enterprise-gateway → cube-server → MNO Gateway",
        "meta": {
            "error_type": "下游超时-MNO",
            "severity": "P0",
            "service": "cube-server", 
            "fix": "同K001",
            "count_2months": 13566,
            "code": "SimServiceImpl.java:836 updateImei"
        }
    },
    {
        "id": "K003",
        "doc": "CB-99-9400 false ERROR on SMS MO. HTTP 200 + business code marked as ERROR. Only CN00000964. latency=0ms. Path: /cube/v4/sms/mo/{iccid}",
        "meta": {
            "error_type": "日志级别误用",
            "severity": "P0",
            "service": "cube-api-v4",
            "fix": "HTTP200+业务码→WARN",
            "count_2months": 36605994
        }
    },
    {
        "id": "K004",
        "doc": "Connection refused to gateway Pod 192.168.136.176. Error: finishConnect failed Connection refused svc-enterprise-gateway. FeignConfig has no Retryer/connection pool/CircuitBreaker",
        "meta": {
            "error_type": "连接失败-Pod",
            "severity": "P0",
            "service": "enterprise-gateway",
            "fix": "K8s Pod排查 + Feign Retryer(3) + ApacheHttpClient + Resilience4j",
            "count_2months": 44362,
            "code": "FeignConfig.java:57"
        }
    },
    {
        "id": "K005",
        "doc": "TimedFeignLogger logs all response headers as ERROR. Each failed Feign call generates ~12 ERROR log lines. FeignConfig line:88 uses log.error() for everything",
        "meta": {
            "error_type": "日志级别误用",
            "severity": "P0",
            "service": "enterprise-gateway",
            "fix": "headers→DEBUG, non2xx→WARN, IOException→ERROR",
            "count_2months": 1093490,
            "code": "FeignConfig.java:88"
        }
    },
    {
        "id": "K006",
        "doc": "sim-service suspend API returns CB-99-9999 with garbled Chinese. SUODO7ZPWA 12 cards × 238 retries each. SimController.pause 35ms → POST svc-sim/suspend → data:?????? null",
        "meta": {
            "error_type": "下游拒绝+编码",
            "severity": "P1",
            "service": "sim-service",
            "fix": "Feign UTF-8 Decoder + 查sim拒绝原因",
            "count_2months": 2856,
            "code": "Feign Decoder / sim-service suspend handler"
        }
    },
    {
        "id": "K007",
        "doc": "Bundle ordering timeout through cube-server to OMS iot-order. POST /cube/v4/sims/{iccid}/bundle → 33695ms → Read timed out POST svc-cube-server/simV4/bundle → omsOrderFeignClient.createOrderByAssetId",
        "meta": {
            "error_type": "下游超时-OMS",
            "severity": "P1",
            "service": "cube-server→OMS",
            "fix": "排查OMS iot-order服务超时",
            "code": "SimApiV4ProxyLockServiceImpl.java:406"
        }
    },
    {
        "id": "K008",
        "doc": "contract-service connect timed out during K8s rolling update. ContractFeignClient#getContract SocketTimeoutException latency=30029ms msg=connect timed out. Midnight 00:20 burst, self-recovered in 30s. No code defect",
        "meta": {
            "error_type": "基础设施-瞬时",
            "severity": "P3",
            "service": "contract-service",
            "fix": "仅需监控告警, 无需修代码",
            "count_2months": "~20",
            "code": "N/A (K8s rolling update)"
        }
    }
]

DOWNSTREAM_SCAN = {
    "total": 22,
    "timeout_continuous": ["cube-server", "sim-service"],
    "timeout_burst": ["contract-service"],
    "http500_rare": ["iot-order"],
    "zero_errors": ["sms-service","enterprise","cdr-aggregating","cdr-persistence",
        "data-pool","base-data","rule-engine","product","order-usage","sphere2-leo",
        "kettle","bbc","rsa","stock","partner","qr-order","production","asset-info"]
}

def seed():
    client, collections = init_chromadb()
    
    print("🌱 写入 8 个已确认问题模式...")
    for p in PATTERNS:
        collections["error_patterns"].add(
            ids=[p["id"]],
            documents=[p["doc"]],
            metadatas=[p["meta"]]
        )
        print(f"  ✅ {p['id']}: {p['meta']['error_type']}")
    
    print("\n🔍 写入 22 下游服务扫描结果...")
    collections["service_topology"].add(
        ids=["downstream_scan"],
        documents=[json.dumps(DOWNSTREAM_SCAN)],
        metadatas=[{"type": "downstream_scan_result", "total": 22}]
    )
    print(f"  ✅ downstream_scan: {DOWNSTREAM_SCAN['total']} services")
    
    print(f"\n✅ 全部写入完成: {len(PATTERNS)} patterns + 1 scan result")

if __name__ == "__main__":
    seed()
