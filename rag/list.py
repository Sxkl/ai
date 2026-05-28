#!/usr/bin/env python3
"""浏览 ChromaDB 中的知识库数据"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chromadb

client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), 'chroma_db'))
col = client.get_collection('fix_knowledge')
results = col.get(include=['documents', 'metadatas'])

if len(sys.argv) > 1:
    keyword = sys.argv[1].lower()
    results['documents'] = [d for d in results['documents'] if keyword in d.lower()]
    print(f'Filter: "{sys.argv[1]}" → {len(results["documents"])} chunks')

for i, doc in enumerate(results['documents']):
    lines = doc.strip().split('\n')
    title = next((l for l in lines if l.startswith('#')), lines[0] if lines else '?')
    print(f'[{i+1:3d}] {title[:100]}')
