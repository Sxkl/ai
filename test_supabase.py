from supabase import create_client

url = "https://yqqrzyctdhxsppqanxnk.supabase.co"
key = "sb_secret_FxuHoUspeW340HQBUkgA-A_sNi57gz3"
client = create_client(url, key)

# 尝试创建 pgvector 扩展和表
sql = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS knowledge_vectors (
    id TEXT PRIMARY KEY,
    source_file TEXT,
    source_filename TEXT,
    chunk_index INTEGER,
    level TEXT,
    category TEXT,
    content TEXT,
    embedding vector(1536),
    file_hash TEXT,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);
"""
try:
    client.rpc("exec_sql", {"query": sql}).execute()
    print("表创建成功")
except Exception as e:
    print(f"用 rpc 创建失败: {e}")
    print("请手动在 Supabase SQL Editor 执行上面的 SQL")

# 测试插入
try:
    result = client.table("knowledge_vectors").select("id", count="exact").limit(1).execute()
    print(f"当前记录数: {result.count}")
except Exception as e:
    print(f"查询测试: {e}")
