#!/usr/bin/env python3
"""
知识图谱 + 向量双路检索

用法:
  python kg_search.py "contract-service 有哪些表"
  python kg_search.py "NPE 怎么修复" --json
"""
import os, sys, json, urllib.request, numpy as np

SUPABASE_URL = "https://yqqrzyctdhxsppqanxnk.supabase.co"
SUPABASE_KEY = "sb_secret_FxuHoUspeW340HQBUkgA-A_sNi57gz3"
DIM = 512

def embed(text):
    vec = np.zeros(DIM)
    for n in range(1, 4):
        for i in range(len(text) - n + 1):
            vec[hash(text[i:i+n]) % DIM] += 1
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist() if norm > 0 else vec.tolist()

def api_rpc(fn, body):
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn}"
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
         "Content-Type": "application/json"}
    req = urllib.request.Request(url, json.dumps(body).encode(), h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return []

def api_get(path):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except:
        return []

# === 双路检索 ===
def search(query, top_k=5):
    vec = embed(query)
    
    # 路1: 向量语义搜索 (nodes embedding)
    vec_results = api_rpc("search_knowledge", {
        "query_embedding": vec, "match_count": top_k, "similarity_threshold": 0.1
    })
    
    # 路2: 图搜索 — 找到匹配的节点，遍历其关系
    graph_results = []
    # 先搜索节点名
    q_lower = query.lower()
    all_nodes = api_get(f"knowledge_nodes?select=*&limit=200")
    matched = [n for n in all_nodes if q_lower in n.get("name","").lower() or q_lower in n.get("description","").lower()][:3]
    
    for n in matched:
        # 获取出边
        out_edges = api_get(f"knowledge_edges?source_id=eq.{n['id']}&select=*&limit=10")
        for e in out_edges:
            target = next((x for x in all_nodes if x["id"] == e["target_id"]), None)
            if target:
                graph_results.append({
                    "source": n, "relation": e["relation"], "target": target,
                    "type": "graph_edge"
                })
        # 获取入边
        in_edges = api_get(f"knowledge_edges?target_id=eq.{n['id']}&select=*&limit=10")
        for e in in_edges:
            source = next((x for x in all_nodes if x["id"] == e["source_id"]), None)
            if source:
                graph_results.append({
                    "source": source, "relation": e["relation"], "target": n,
                    "type": "graph_edge"
                })

    return {
        "vector_results": vec_results[:top_k],
        "graph_results": graph_results[:top_k],
        "query": query
    }

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("query")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = search(args.query)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f'\n🔍 查询: "{args.query}"\n')
        
        print("=== 向量语义召回 ===")
        for r in result["vector_results"][:3]:
            print(f"  [{r.get('similarity',0):.4f}] {r.get('source_filename','')}: {r.get('content','')[:80]}")
        
        print(f"\n=== 知识图谱关系 (共{len(result['graph_results'])}条) ===")
        for r in result["graph_results"][:5]:
            src = r["source"]["name"]
            tgt = r["target"]["name"]
            rel = r["relation"]
            print(f"  [{src}] ──{rel}──▶ [{tgt}]")
