"""
对话记录器 — 每条对话自动向量化存入 Supabase

所有 agent 每轮对话调用此模块自动保存
"""
import os, json, uuid, urllib.request, numpy as np
from datetime import datetime

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

def log_turn(session_id, agent_name, role, content, tokens=0, tool_calls=None):
    """记录一轮对话"""
    record = {
        "id": str(uuid.uuid4())[:16],
        "session_id": session_id,
        "agent_name": agent_name,
        "role": role,
        "content": content[:4000],
        "embedding": embed(content[:2000]),
        "tokens_used": tokens,
        "tool_calls": json.dumps(tool_calls or []),
        "created_at": datetime.utcnow().isoformat()
    }
    url = f"{SUPABASE_URL}/rest/v1/conversations"
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
         "Content-Type": "application/json", "Prefer": "return=minimal"}
    req = urllib.request.Request(url, json.dumps(record).encode(), h, method="POST")
    try: urllib.request.urlopen(req, timeout=10)
    except: pass

def search_conversations(query, top_k=5):
    """搜索历史对话"""
    vec = embed(query)
    body = {"query_embedding": vec, "match_count": top_k, "similarity_threshold": 0.15}
    url = f"{SUPABASE_URL}/rest/v1/rpc/search_conversations"
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, json.dumps(body).encode(), h)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except: return []

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        results = search_conversations(sys.argv[1])
        for r in results:
            print(f"[{r.get('similarity',0):.4f}] [{r.get('agent_name','')}] {r.get('content','')[:120]}")
    else:
        log_turn("demo", "test", "user", "测试消息")
        print("测试消息已记录")
