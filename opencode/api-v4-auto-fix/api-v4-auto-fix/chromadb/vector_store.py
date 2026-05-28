"""
api-v4-auto-fix 轻量级向量检索器 (不依赖 ChromaDB)

基于 TF-IDF + 关键词匹配的 fallback 实现。
当 ChromaDB 不可用时自动降级使用此模块。

用法:
  from vector_store import VectorStore
  store = VectorStore("knowledge/vectors.json")
  results = store.query("Connection refused gateway")
"""

import json
import os
import math
from collections import Counter

class VectorStore:
    """轻量级向量存储 — 基于 TF-IDF 相似度"""
    
    def __init__(self, vectors_path):
        self.vectors_path = vectors_path
        self.patterns = []
        self.idf = {}
        self._load()
        self._build_index()
    
    def _load(self):
        path = os.path.join(os.path.dirname(__file__), "..", self.vectors_path)
        with open(self.vectors_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.patterns = data["patterns"]
    
    def _tokenize(self, text):
        """简单分词: 按空格/标点拆分 + 小写化"""
        import re
        tokens = re.split(r'[\s,;:.!?()\[\]{}\'\"\-_/]+', text.lower())
        return [t for t in tokens if len(t) > 1]
    
    def _build_index(self):
        """构建 IDF 索引"""
        N = len(self.patterns)
        doc_freq = Counter()
        for p in self.patterns:
            tokens = set(self._tokenize(" ".join(p["keywords"])))
            for t in tokens:
                doc_freq[t] += 1
        self.idf = {t: math.log((N + 1) / (f + 1)) + 1 for t, f in doc_freq.items()}
    
    def _vectorize(self, text):
        """将文本转为 TF-IDF 向量"""
        tokens = self._tokenize(text)
        tf = Counter(tokens)
        vec = {}
        for t, f in tf.items():
            if t in self.idf:
                vec[t] = f * self.idf[t] / len(tokens)
        return vec
    
    def _cosine_similarity(self, v1, v2):
        """计算两个稀疏向量的余弦相似度"""
        dot = sum(v1.get(k, 0) * v2.get(k, 0) for k in set(v1) | set(v2))
        norm1 = math.sqrt(sum(x**2 for x in v1.values()))
        norm2 = math.sqrt(sum(x**2 for x in v2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0
        return dot / (norm1 * norm2)
    
    def query(self, text, top_k=5):
        """查询最相似的模式"""
        query_vec = self._vectorize(text)
        results = []
        
        for p in self.patterns:
            pattern_vec = self._vectorize(" ".join(p["keywords"]))
            keyword_score = self._cosine_similarity(query_vec, pattern_vec)
            
            # 直接关键词匹配加分
            direct_match = sum(
                1 for kw in p["keywords"] 
                if kw.lower() in text.lower()
            )
            
            combined_score = keyword_score * 0.7 + (direct_match / max(len(p["keywords"]), 1)) * 0.3
            
            results.append({
                "pattern": p,
                "score": combined_score,
                "keyword_match": direct_match
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def query_by_error(self, error_text, top_k=3):
        """根据错误文本匹配最佳修复方案"""
        results = self.query(error_text, top_k)
        return [{
            "pattern_id": r["pattern"]["id"],
            "error_type": r["pattern"]["error_type"],
            "severity": r["pattern"]["severity"],
            "root_cause": r["pattern"]["root_cause"],
            "fix": r["pattern"]["fix"],
            "fix_code_location": r["pattern"]["fix_code_location"],
            "confidence": f"{r['score']:.2f}"
        } for r in results if r["score"] > 0.1]


# 预初始化实例
_store = None

def get_store():
    global _store
    if _store is None:
        vectors_path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "vectors.json")
        _store = VectorStore(vectors_path)
    return _store


if __name__ == "__main__":
    store = get_store()
    
    # 测试查询
    test_queries = [
        "Connection refused to enterprise-gateway service",
        "Feign logger is logging response headers as ERROR",
        "SMS MO messages returning CB-99-9400",
        "Chinese characters showing as question marks in response",
    ]
    
    for q in test_queries:
        print(f"\n🔍 查询: \"{q}\"")
        results = store.query_by_error(q)
        for i, r in enumerate(results):
            print(f"  #{i+1} [{r['pattern_id']}] {r['error_type']} (置信度:{r['confidence']})")
            print(f"       修复: {r['fix'][:80]}...")
