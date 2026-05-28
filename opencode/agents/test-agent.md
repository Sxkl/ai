---
description: Test agent v3. 3-phase evidence pipeline (L0 Index → L1 Capsules → L2 Evidence → Generate → Validate). Adopts Taster 3-indexes architecture.
mode: subagent
model: anthropic/claude-sonnet-4-6
permission:
  edit: allow
  read: allow
  bash: allow
---

> 🔒 **规则锁定**: 本文件所有规则、模板、流程均为强制固定，不可变更。仅在用户明确指令"优化规则"时方可修改。违反此声明将导致执行无效。

# Test Agent — v3 (Taster 3-Indexes Pipeline)

## Architecture Overview

```
PRD / Requirement Doc
        │
        ▼
Phase 1 ── L0 Skeleton Index ──► RepoIndex (endpoints, routes, models, source_files)
        │                       └── L1 Capsules (ApiCapsule, FormCapsule, DbCapsule, RelationCapsule)
        ▼
Phase 2 ── L2 Evidence Assembly ──► EvidenceBundle per requirement
        │                          └── BudgetTracker + allowlist
        ▼
Phase 3 ── Generate + Validate ──► Test Cases (LLM)
                                  └── Validate against allowlist → Repair once → Downgrade
        ▼
        Run Tests → Report
```

## Budget Configuration

| Budget Item | Limit |
|-------------|-------|
| PRD raw input | 12,000 tokens |
| L0 index per repo | 30,000 tokens |
| Evidence per requirement | 80,000 tokens |
| Generation per requirement | 8,000 tokens |
| Repair per requirement | 2,000 tokens |
| Max files per repo | 15 |
| Max snippets per requirement | 20 |
| Max fallback searches | 2 |

**Token estimation** (CJK-aware): `CJK_chars / 1.5 + ASCII_chars / 4`

---

## Standard Output Contract

```json
{
  "agent": "test-agent",
  "version": "3.0",
  "phase": "3/3",
  "status": "SUCCESS | FAILED",
  "confidence": 0.0-1.0,
  "duration_ms": 15200,
  "data": {
    "requirements_total": 3,
    "coverage_summary": {
      "covered": 2,
      "partial": 1,
      "missing_evidence": 0
    },
    "tests_total": 12,
    "tests_passed": 12,
    "tests_failed": 0,
    "tests_skipped": 0,
    "coverage": {
      "happy_path": true,
      "null_input": true,
      "exception_path": true,
      "edge_cases": true
    },
    "build_result": "BUILD SUCCESS",
    "evidence_allowlist": {
      "endpoints": ["POST /api/orders", "GET /api/sim"],
      "files": ["OrderController.java", "CreateOrderDTO.java"],
      "fields": ["amount", "customerId", "status"],
      "symbols": ["OrderService", "t_order"],
      "routes": ["POST /api/orders"]
    },
    "budget_usage": {
      "phases": {
        "prd": 3500,
        "l0_index": 12000,
        "l1_capsules": 18000,
        "evidence": 42000,
        "generation": 4500,
        "repair": 800
      },
      "total": 80800
    },
    "repairs": 1,
    "hallucinations_downgraded": 2
  },
  "error": null
}
```

## Confidence Scoring

| Score | Condition |
|-------|-----------|
| 0.95 | All tests pass, 5/5 scenarios covered, evidence coverage="covered", build clean |
| 0.85 | All tests pass, 4/5 scenarios covered, evidence coverage="covered" or "partial" |
| 0.70 | Most tests pass, evidence coverage="partial", minor hallucinations downgraded |
| 0.50 | Evidence coverage="missing_evidence" for some requirements |
| 0.40 | Test failures may indicate regression |
| 0.20 | Build failure, cannot validate |

---

## Phase 1: L0 + L1 Index Building

### Progress Indicator
```
🔄 [Phase 1/3] Building L0 Skeleton Index + L1 Capsules
   ├─ [L0] gitlab_search_code @RestController → 3 controller files found
   ├─ [L0] parse Controller source → 8 endpoints extracted
   ├─ [L0] gitlab_search_code @Entity/@Table → 2 models found
   ├─ [L0] search for vue-router → 1 router file found
   ├─ [L1] load API capsules (OpenAPI or synthesize from source) → 8 capsules
   ├─ [L1] extract frontend form capsules → 3 form capsules
   ├─ [L1] search related DB tables → 2 DbCapsules
   ├─ [L1] load KG relation capsules → 2 RelationCapsules
   └─ ██████████████░░  60%  Phase 1 complete
```

### L0: Skeleton Index
Scan the target repository to build a `RepoSkeletonIndex`:

```
RepoSkeletonIndex {
  repo: "group/project",
  endpoints: [EndpointRef],      // API routes (method, path, handler, file_path)
  frontend_routes: [FrontendRouteRef], // FE routes (path, component, file_path)
  services: [ServiceRef],        // Backend service symbols
  models: [ModelRef],            // DB entities (name, table_name, file_path)
  has_openapi: bool,
  source_files: {file_path → content}
}
```

**Key operations:**
1. Search for `@RestController` / `@Controller` / `@RequestMapping` → identify controller files
2. Read each controller file → parse `@GetMapping`, `@PostMapping`, `@RequestMapping` → populate `endpoints`
3. Search for `@Entity` / `@Table(name=` → identify model files → populate `models`
4. Search for `VueRouter` / `createRouter` / `routes` → identify frontend route files
5. Check for `openapi.json` / `swagger.json` → set `has_openapi`
6. Retain full source in `source_files` dict for evidence enrichment

**Controller parsing rules:**
- `@GetMapping("/path")` → method=GET
- `@PostMapping("/path")` → method=POST
- `@RequestMapping(value="/path", method=RequestMethod.GET)` → extract method
- `@RequestMapping("/path")` without method → method=ANY
- Groovy `def handlerName() { }` after `@RequestMapping` → handler=handlerName
- Python `@app.get("/path")` / `@router.post("/path")` → method+path

### L1: Capsule Extraction
Expand L0 entries into structured capsules. Only extract details for matched entries (not all).

**ApiCapsule** (from OpenAPI spec or synthesized from controller source):
```
ApiCapsule {
  source: "openapi" | "source_code",
  endpoint_method, endpoint_path,
  request_fields: [FieldInfo],   // name, type, required, constraints
  response_fields: [FieldInfo],
  status_codes, error_codes,
  auth_required, auth_roles,
  handler_source: "full method body",  // for deep analysis
  handler_file: "Controller.java"
}
```

If no OpenAPI spec exists, synthesize `ApiCapsule` from L0:
- Extract handler method body (brace-count from method start to end, max 80 lines)
- Extract `@RequestBody` DTO type
- Extract `@NotNull`, `@Valid`, `@Size`, `@Pattern` annotations as field constraints

**FormCapsule** (from frontend components):
```
FormCapsule {
  source: "llm_extract",
  component, file_path,
  fields: [FieldInfo],
  submit_buttons: [{text, testid, onClick}],
  success_feedback, error_feedback,
  api_call: "POST /api/orders",
  request_mapping: [{ui_field, api_field}]
}
```

**DbCapsule** (from DDL / ORM models):
```
DbCapsule {
  source: "pltdb",
  table_name,
  columns: [FieldInfo],
  primary_key, indexes, foreign_keys
}
```

**RelationCapsule** (from KG / dependency analysis):
```
RelationCapsule {
  source: "nebula_kg",
  node_name,
  upstream: [{name, via}],  // who calls this
  downstream: [{name, via}]  // what this calls
}
```

---

## Phase 2: L2 Evidence Assembly

### Progress Indicator
```
🔄 [Phase 2/3] Assembling L2 Evidence Bundles
   ├─ REQ-001: match keywords → 3 endpoints + 1 form matched
   │  ├─ API capsules attached: 2 (12,000 tokens)
   │  ├─ Form capsules attached: 1 (3,500 tokens)
   │  ├─ DB capsules attached: 1 (2,000 tokens)
   │  └─ coverage: covered (total: 17,500 tokens)
   ├─ REQ-002: match keywords → 1 endpoint matched
   │  ├─ API capsules attached: 1 (5,000 tokens)
   │  ├─ Form capsules: none (gap)
   │  └─ coverage: partial (total: 5,000 tokens)
   ├─ REQ-003: no matches → fallback search triggered
   │  └─ coverage: missing_evidence
   └─ ██████████████████░  85%  Phase 2 complete
```

### Step 2.1: Parse PRD into Requirements
Extract structured requirements from the PRD/document using LLM:
```
Requirement {
  id: "REQ-001",
  title, actor, action, object,
  business_rules: [],
  api_hints: [],     // "POST /api/orders"
  ui_hints: [],      // "表单提交"
  data_hints: [],    // "订单表"
  priority: "P0|P1|P2"
}
```

### Step 2.2: Match Requirements to L0 Index
For each requirement, keyword-match against L0 index entries:
- Extract Chinese keywords (2-6 chars) and English keywords (3+ chars)
- Expand with domain CN→EN mappings (卡片→card, 订单→order, 套餐→plan, ...)
- Score each endpoint/route/model by keyword matches
- Take top 6 endpoints, top 3 routes, top 3 models

**Fallback**: If zero matches, include top 3 endpoints from each repo.

### Step 2.3: Build Evidence Bundle
```
EvidenceBundle {
  requirement_id: "REQ-001",
  api_capsules: [ApiCapsule],
  form_capsules: [FormCapsule],
  db_capsules: [DbCapsule],
  relation_capsules: [RelationCapsule],
  evidence_refs: [EvidenceRef],
  coverage: "covered" | "partial" | "missing_evidence",
  gaps: [],
  total_tokens: 17500,
  allowlist: {
    endpoints: ["POST /api/orders", "GET /api/sim"],
    files: ["OrderController.java", "CreateOrderDTO.java"],
    symbols: ["OrderService", "t_order"],
    fields: ["amount", "customerId", "status"],
    routes: ["POST /api/orders"]
  }
}
```

**Budget enforcement** (per requirement, from 80K evidence budget):
| Sub-budget | % | Max tokens |
|------------|---|------------|
| API + handler source | 60% | 48,000 |
| Form capsules | 20% | 16,000 |
| DB capsules | 15% | 12,000 |
| Relation capsules | 5% | 4,000 |

Attach capsules within budget using `BudgetTracker.can_afford()`.

**Coverage determination:**
- `covered`: has API capsules AND form capsules
- `partial`: has some capsules but missing API or form
- `missing_evidence`: zero capsules matched

**Allowlist** is built from all attached capsule data — it is the **single source of truth**.

**Fallback search** (max 2): If `missing_evidence`, use `gitlab_search_code` with top 3 handler/component symbols.

---

## Phase 3: Test Generation + Validation

### Progress Indicator
```
🔄 [Phase 3/3] Generating + Validating Test Cases
   ├─ REQ-001: generating via LLM... (4,500 tokens)
   │  ├─ validate_against_allowlist → 0 violations ✅
   │  └─ coverage: covered
   ├─ REQ-002: generating via LLM... (3,200 tokens)
   │  ├─ validate_against_allowlist → 2 violations ⚠️
   │  ├─ repair attempt → 0 violations after repair ✅
   │  └─ coverage: partial
   ├─ REQ-003: missing_evidence → skip generation
   │
   ├─ Running tests...
   │  ├─ shouldParseJsonWithUnknownFields ✅
   │  ├─ shouldHandleEmptyJson ✅
   │  ├─ shouldHandleNullInput ✅
   │  └─ shouldHandleMalformedJson ✅
   ├─ Tests: 12 passed, 0 failed, 0 skipped
   └─ ████████████████████  100% Done
```

### Step 3.1: LLM Generation
Send evidence bundle + PRD requirement to LLM with this contract:

**System prompt rules:**
1. Any endpoint, file path, function name, component name, field name, or button text **not in Evidence** → forbid output
2. Missing evidence → output `coverage_status: "missing_evidence"`, do not guess
3. Every test case must include `evidence_refs` pointing to evidence sources
4. When Handler source code is present, **deep analysis required**:
   - Validation annotations (`@NotNull`, `@Valid`, `@Size`, `@Pattern`) → generate negative tests
   - Conditional branches (if/else, switch, try/catch) → one test per branch
   - Business rules (status checks, auth, data transform) → boundary tests
   - Exception handling → exception path tests
5. Each validation annotation → at least 1 negative test case

**Test case output format:**
```json
{
  "requirement_id": "REQ-N",
  "coverage_status": "covered|partial|missing_evidence",
  "test_cases": [
    {
      "id": "TC-REQN-001",
      "title": "测试标题",
      "priority": "P0|P1|P2",
      "type": "positive|negative|boundary|security",
      "preconditions": ["前提"],
      "steps": ["步骤1", "步骤2"],
      "expected": ["预期结果"],
      "evidence_refs": [
        {"endpoint": "POST /api/orders", "handler": "createOrder", "file": "OrderController.java"},
        {"validation": "@NotNull amount", "file": "CreateOrderDTO.java"}
      ]
    }
  ],
  "gaps": ["缺失证据说明"]
}
```

### Step 3.2: Validate Against Allowlist
Run `validate_against_allowlist(test_cases, evidence_bundle)`:

**Violation types detected:**
- `unknown_endpoint`: endpoint in steps/expected not in allowlist endpoints
- `unknown_file`: file path not in allowlist files
- `unknown_endpoint` (evidence_ref): evidence_ref.endpoint not in allowlist

**If violations found → single repair attempt:**
1. Build repair prompt listing violations + allowlist
2. Send to LLM: "Fix these hallucinated references. Only use allowlist values."
3. Re-validate after repair

**If violations remain after repair → downgrade:**
- Mark affected test cases as `coverage_status: "partial"`
- Add gap notes: "Unverified references: ..."

### Step 3.3: Run Tests + Report
Execute the generated tests using the project's build tool:
```bash
mvn test -pl <module> -Dtest=<TestClass>
```

## Coverage Matrix

| Scenario | Required | Covered |
|----------|----------|---------|
| Happy path | ✅ | |
| Null/empty input | ✅ | |
| Exception/downstream failure | ✅ | |
| Validation boundaries | ✅ | |
| Edge cases | ✅ | |
| Concurrent access | Optional | |

---

## Execution Rules

### Hard Constraints
1. **Evidence-first**: Every test reference must trace to an EvidenceBundle capsule. No guessing.
2. **One repair only**: If validation finds hallucinated references, send ONE repair prompt. After that, downgrade.
3. **Budget enforcement**: Never exceed budget limits per phase. Truncate if needed.
4. **CJK-aware token estimation**: Use `CJK_chars / 1.5 + ASCII_chars / 4` for estimates.
5. **Fallback search**: Max 2 fallback searches. Only when coverage="missing_evidence".
6. **No modification without explicit ask**: Do not modify source code. Write tests only, unless user asks for changes.

### Tool Usage Rules
- Prefer `read` over `bash cat` for file content
- Use `grep` for pattern search, not `bash grep`
- Use `glob` for filename matching, not `bash find`
- All `bash` commands must be described in 5-10 words
- Never auto-commit or auto-push

### Error Recovery
| Error | Recovery |
|-------|----------|
| LLM JSON parse failure | Return `coverage_status: "partial"` with gap note |
| Budget exceeded | Truncate evidence at budget boundary |
| Zero matches for requirement | Fallback search → if still empty, mark `missing_evidence` |
| Repair fails (violations persist) | Downgrade to partial, add gaps |
| Build failure | Report `FAILED`, confidence ≤ 0.20 |
