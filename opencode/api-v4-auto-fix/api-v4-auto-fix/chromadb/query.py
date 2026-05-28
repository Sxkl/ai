"""
ChromaDB 查询接口 — 向量相似度检索已知问题模式

用法:
  python query.py "Connection refused to gateway"
  python query.py --top-k 5 --collection error_patterns "Feign timeout"
"""

import argparse
from init_db import init_chromadb

def query_similar(query_text, collection_name="error_patterns", top_k=5):
    """查询与给定文本最相似的模式"""
    _, collections = init_chromadb()
    
    if collection_name not in collections:
        collections_list = list(collections.keys())
        print(f"❌ 集合 '{collection_name}' 不存在. 可用: {collections_list}")
        return
    
    collection = collections[collection_name]
    
    results = collection.query(
        query_texts=[query_text],
        n_results=top_k
    )
    
    print(f"\n🔍 查询: \"{query_text}\"")
    print(f"📂 集合: {collection_name}")
    print(f"📊 结果: {len(results['ids'][0])} 条\n")
    
    for i, (doc_id, doc, meta, dist) in enumerate(zip(
        results["ids"][0], results["documents"][0], 
        results["metadatas"][0], results["distances"][0]
    )):
        similarity = max(0, 1 - dist) * 100  # cosine distance → similarity %
        print(f"{'─'*60}")
        print(f"#{i+1} [{doc_id}] 相似度: {similarity:.1f}%")
        if collection_name == "error_patterns":
            print(f"   类型: {meta.get('error_type', 'N/A')}")
            print(f"   严重度: {meta.get('severity', 'N/A')}")
            print(f"   代码位置: {meta.get('code_location', 'N/A')}")
            print(f"   出现次数: {meta.get('observed_count', 'N/A')}")
            print(f"   修复方案: {meta.get('fix_pattern', 'N/A')}")
        elif collection_name == "fix_patterns":
            print(f"   分类: {meta.get('category', 'N/A')}")
            print(f"   代码修改: {meta.get('code_change', 'N/A')[:100]}...")
            print(f"   验证方式: {meta.get('verification', 'N/A')}")
        elif collection_name == "service_topology":
            print(f"   类型: {meta.get('type', 'N/A')}")
            print(f"   故障影响: {meta.get('failure_impact', 'N/A')}")
    print(f"{'─'*60}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChromaDB 已知模式查询")
    parser.add_argument("query", help="查询文本")
    parser.add_argument("--collection", "-c", default="error_patterns",
                       choices=["error_patterns", "fix_patterns", "service_topology"])
    parser.add_argument("--top-k", "-k", type=int, default=5)
    args = parser.parse_args()
    query_similar(args.query, args.collection, args.top_k)
