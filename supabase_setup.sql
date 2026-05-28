-- 1. 启用 pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 知识向量表
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

-- 3. IVFFlat 索引
CREATE INDEX IF NOT EXISTS idx_kv_embedding
ON knowledge_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 4. 搜索存储过程
CREATE OR REPLACE FUNCTION search_knowledge(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.4,
    filter_level TEXT DEFAULT NULL,
    filter_category TEXT DEFAULT NULL
)
RETURNS TABLE(
    id TEXT,
    source_filename TEXT,
    level TEXT,
    category TEXT,
    content TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        k.id,
        k.source_filename,
        k.level,
        k.category,
        k.content,
        1 - (k.embedding <=> query_embedding) AS similarity
    FROM knowledge_vectors k
    WHERE 1 - (k.embedding <=> query_embedding) > similarity_threshold
      AND (filter_level IS NULL OR k.level = filter_level)
      AND (filter_category IS NULL OR k.category = filter_category)
    ORDER BY k.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
