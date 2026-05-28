# Stargate Architecture Patterns

> 来源: platform/stargate/stargate | 分析时间: 2026-05-18

## MCP 连接池单例模式

Stargate 通过 `MCPManager` 单例管理 5 个外部 MCP 服务器连接:
- feishu (SSE), nebula (streamable), pltdb (streamable), jira (streamable), gitlab (streamable)
- 关键特性: 自动重连、工具列表缓存、Nebula key 注入、工具只读检测
- 故障恢复: 调用失败时自动 `reconnect()` 后重试

## 统一 LLM 路由

所有 LLM 调用通过 `ModelManager` → OpenRouter 单一出口:
- provider routing: model name 必须带前缀 (e.g. `anthropic/claude-sonnet-4`)
- role 解析: `resolve_role(role)` 映射到具体模型
- 默认模型优先级: admin API key > default role model

## Skill 系统 DSL

技能定义存储为 JSON DAG steps:
- 7 种 step 类型: mcp_tool, llm_call, http_call, kg_query, kg_write, sub_skill, gate, custom
- 执行生命周期: pending → queued → running → done/error/cancelled/waiting_approval
- 4 Worker 进程内队列，支持 cancel/retry/chain
- 幂等键: idempotency_key 防止重复执行
- 预算控制: budget_usd, budget_chunks, timeout_seconds

## Fernet 加密模式

所有 secret 统一通过 Fernet 加密存储在 `app_settings` 或 `user_tokens` 表:
- TOKEN_ENCRYPTION_KEY 必须永不更改
- `encrypt_token()` / `decrypt_token()` / `mask_secret()` API

## 3 轮对抗审查 (MR Review)

Adversarial review pipeline:
- Round 1: AI 审查代码 → 生成 findings
- Round 2: 开发者 dispute → 生成 suppressions
- Round 3: 最终裁定 → 生成最终报告
- 模型: mr_reviews, mr_review_findings, mr_review_suppressions

## Taster 三索引测试生成

证据绑定的测试用例生成:
- L0: RepoSkeletonIndex (文件结构索引)
- L1: ApiCapsule / FormCapsule / DbCapsule / RelationCapsule (语义胶囊)
- L2: EvidenceBundle / EvidenceRef (证据绑定)
- 预算控制: BudgetTracker 限制 token 消耗
- 验证: 生成结果与 evidence allowlist 交叉验证

## 认证多层架构

- Authing OIDC: JWT Bearer + JWKS 缓存 (6h TTL, async Lock)
- API Key: X-API-Key header (CI/CD 集成)
- Service Key: X-Service-Key header (内部 LLM 服务)
- Developer Key: X-Developer-Key → LLM Relay (MCP 外部调用)
- Webhook: X-Webhook-Token / X-Gitlab-Token / X-Hub-Signature

## ASGI 审计中间件

纯 ASGI 中间件记录每个 API 请求:
- 自动记录: user_id, action, resource_type, detail (JSON), ip_address
- 用户名缓存: 500-entry LRU 减少 DB 查询
- 模型: audit_logs 表
