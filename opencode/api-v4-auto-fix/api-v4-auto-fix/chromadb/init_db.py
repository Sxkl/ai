"""
api-v4-auto-fix ChromaDB 知识库初始化

初始化 ChromaDB 集合, 用于存储和检索已知错误模式、根因、修复方案。
"""

import os
import json
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "data")

def init_chromadb():
    """初始化 ChromaDB 客户端和集合"""
    
    os.makedirs(CHROMA_PATH, exist_ok=True)
    
    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False)
    )
    
    # 使用 sentence-transformers 作为嵌入模型 (中文友好)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    # 创建三个集合: 错误模式、修复方案、服务拓扑
    collections = {}
    
    # 1. 错误模式集合
    try:
        client.delete_collection("error_patterns")
    except:
        pass
    collections["error_patterns"] = client.create_collection(
        name="error_patterns",
        embedding_function=embedding_fn,
        metadata={"description": "已知错误模式: 错误信息 → 根因 → 代码位置"}
    )
    
    # 2. 修复方案集合
    try:
        client.delete_collection("fix_patterns")
    except:
        pass
    collections["fix_patterns"] = client.create_collection(
        name="fix_patterns",
        embedding_function=embedding_fn,
        metadata={"description": "已知修复方案: 问题描述 → fix代码 → 验证方式"}
    )
    
    # 3. 服务拓扑集合
    try:
        client.delete_collection("service_topology")
    except:
        pass
    collections["service_topology"] = client.create_collection(
        name="service_topology",
        embedding_function=embedding_fn,
        metadata={"description": "服务拓扑: 服务名 → 依赖关系 → 故障影响"}
    )
    
    print(f"✅ ChromaDB 初始化完成: {CHROMA_PATH}")
    print(f"   集合: {list(collections.keys())}")
    return client, collections

if __name__ == "__main__":
    init_chromadb()
