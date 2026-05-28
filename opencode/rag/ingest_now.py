"""
知识库导入 Supabase — 纯 Python 内置库 + numpy
"""
import os, sys, json, hashlib, urllib.request, urllib.error, re
from pathlib import Path
import numpy as np

SUPABASE_URL = "https://yqqrzyctdhxsppqanxnk.supabase.co"
SUPABASE_KEY = "sb_secret_FxuHoUspeW340HQBUkgA-A_sNi57gz3"
TABLE = "knowledge_vectors"
DIM = 512  # 向量维度

def supabase_api(method, path, body=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json", "Prefer": "return=representation"
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code == 409:
            return {}
        print(f"  API错误 [{e.code}]: {body[:150]}")
        return None

def embed_text(text, dim=DIM):
    """轻量向量化: 字符ngram哈希 → 单位向量"""
    vec = np.zeros(dim)
    # 1-3 gram 字符哈希
    for n in range(1, 4):
        for i in range(len(text) - n + 1):
            h = hash(text[i:i+n]) % dim
            vec[h] += 1
    # 归一化
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

def simple_chunk(text, size=600):
    """按段落+长度分块"""
    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) < size:
            current += p + "\n\n"
        else:
            if current.strip(): chunks.append(current.strip())
            current = p + "\n\n"
    if current.strip(): chunks.append(current.strip())
    return chunks

# === 读取 .env ===
env_path = Path(os.path.expanduser("~/Desktop/ai-auto-study/.env"))
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

# === 主流程 ===
base = Path(os.path.expanduser("~/.config/opencode/knowledge"))
files = list(base.rglob("*.md"))
print(f"文件数: {len(files)}, 向量维度: {DIM}")

# 清空
supabase_api("DELETE", f"{TABLE}?id=neq.__keep__")
print("旧数据已清空")

total = 0
for md_file in sorted(files):
    try:
        content = md_file.read_text(encoding="utf-8")
    except:
        continue

    chunks = simple_chunk(content)
    fhash = hashlib.md5(content.encode()).hexdigest()
    path_str = str(md_file)

    level = ""
    if "/L1-" in path_str: level = "L1"
    elif "/L2-" in path_str: level = "L2"
    elif "/L3-" in path_str: level = "L3"

    cat = "unknown"
    if "/patterns/" in path_str: cat = "pattern"
    elif "/services/" in path_str: cat = "service"
    elif md_file.name.startswith("K") or md_file.name.startswith("N"): cat = "fix"

    valid = [c for c in chunks if len(c.strip()) >= 50]
    if not valid:
        continue

    rows = []
    for i, chunk in enumerate(valid):
        rows.append({
            "id": f"{md_file.name}:{i}",
            "source_file": str(md_file),
            "source_filename": md_file.name,
            "chunk_index": i,
            "level": level,
            "category": cat,
            "content": chunk,
            "embedding": embed_text(chunk),
            "file_hash": fhash,
        })

    # 批量插入 20 条
    for i in range(0, len(rows), 20):
        supabase_api("POST", TABLE, rows[i:i+20])

    total += len(rows)
    rel = str(md_file.relative_to(Path.home()))
    print(f"  [{total}] {rel} ({len(rows)}条)")

print(f"\n=== 导入完成! Supabase 共 {total} 条 ===")
