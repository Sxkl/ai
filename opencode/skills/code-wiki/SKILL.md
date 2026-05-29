---
name: code-wiki
description: AI-Native 代码知识库，对标 Google Code Wiki。扫描仓库生成活文档、类图、架构图，自然语言问代码。触发关键词：读代码、扫描仓库、代码结构、架构图、类图、依赖分析、code wiki、scan repo。
---

# Code Wiki Skill — 读代码 + 活文档 + 架构图

## 触发条件

用户提到以下关键词时自动触发：
- 读代码 / 理解代码 / 代码做了什么
- 扫描仓库 / scan repo / ingest
- 架构图 / 类图 / 依赖图 / ER 图
- 接口依赖 / 调用链 / 影响分析
- code wiki / 活文档

## 工作流

### 1. 扫描仓库 → 生成知识图谱

```bash
# 全量扫描 (首次)
→ kg_ingest_code(repo_id="group/project", branch="develop")
→ kg_code_ingest_status(task_id) # 等待完成

# 增量扫描 (日常)
→ kg_ingest_code(repo_id="group/project", diff_mode=true)
```

### 2. 自然语言问代码

```
用户问 → 分解意图 → 多路检索 → 读源码 → 结构化回答

检索路径:
  ├─ kg_concept_search(keywords)     # 概念匹配
  ├─ kg_code_locate(concept_id)      # 代码定位
  ├─ gitlab_search_code(query)       # 全文搜索
  ├─ kg_rag_search(query)            # RAG 增强
  └─ gitlab_get_file(path, ref)      # 读源码
```

回答格式:
```markdown
## 功能说明
{一句话概括}

## 核心逻辑
{关键流程步骤}

## 调用链
`Caller → Target → Downstream`

## 依赖关系
- 数据库表: {tables}
- 下游服务: {services}
- 缓存键: {redis_keys}

## 相关概念 (来自知识图谱)
{KG 关联节点}
```

### 3. 生成架构图

根据 KG 关系自动生成 Mermaid 图:

```
→ kg_impact_analysis(node_id, direction="both", depth=2)
→ kg_list_relations(source_id=node_id)
→ 选择图表类型 (flowchart / classDiagram / sequenceDiagram / erDiagram)
→ 生成 Mermaid 源码
→ (可选) mermaid_to_feishu(code, doc_token)
```

### 4. PR 审查增强 (KG 上下文注入)

在 review-agent 执行前，先获取变更文件的 KG 上下文:

```
→ kg_context_for_pr(changed_files=[...], repo_id="...")
→ 返回: 受影响的业务概念 / 服务 / 数据实体
→ 注入到 review-agent 的审查上下文中
```

### 5. 影响分析

```
→ kg_impact_analysis(node_id, direction="both", depth=3)
→ pltdb_analyze_impact(table_name, change_description)  # 数据库层面
→ 合并输出: 影响范围报告
```

## 常用组合命令

| 场景 | 命令示例 |
|------|---------|
| 首次扫描 | "扫描 sphere2-business-support 仓库" |
| 日常更新 | "增量更新 contract-service 的代码知识" |
| 问代码 | "ContractService.export 方法做了什么" |
| 画架构图 | "画 contract-service 的服务依赖图" |
| 画类图 | "画 ContractService 的类关系图" |
| 影响分析 | "修改 contract 表的 status 字段会影响什么" |
| PR 上下文 | "给这个 MR 的变更文件生成 KG 上下文" |
