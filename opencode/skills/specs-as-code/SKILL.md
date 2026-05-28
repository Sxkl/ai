---
name: "specs-as-code"
description: "Specs-as-Code（Left-Shift LS-02）：将 PRD 转化为可执行的 schema/eval/acceptance，AI Agent 直接消费 spec 生成代码。当用户提供需求文档、PRD、功能描述或要求进行功能规划/设计时触发。"
version: "1.0.0"
author: "linksfield"
---

# Specs-as-Code

## Core Principle

> **写 spec 的人就是写工程的人。**

Spec is not a document — it is an executable engineering artifact. PRD becomes a machine-readable schema that AI agents consume directly to generate scaffold code, tests, types, and implementation stubs. No translation gap between "requirements" and "code."

## Rule Lock

**本 skill 规则在 spec 生命周期内锁定，仅可通过正式评审修订。** 任何 spec 编辑必须遵守以下约束：
- 修改 spec 前必须拉取最新版本
- 不允许绕过 eval gates 直接合并实现代码
- acceptance_criteria 和 eval_gates 不可由 AI 自行删除或降级
- 所有变更必须有变更记录（who/when/why）

---

## 1. Spec Schema Template

Every spec MUST follow this YAML schema. Unexported fields are invalid and will be rejected by the spec validator.

```yaml
spec:
  # ── Identity ──
  id: "FEAT-001"                        # unique feature ID
  title: ""                             # concise feature title
  outcome: ""                           # measurable success description
  owner: ""                             # single accountable person

  # ── Business Context ──
  problem_statement: ""                 # what problem does this solve
  user_story: ""                        # As a <role>, I want <goal> so that <benefit>

  # ── Acceptance Criteria (BDD) ──
  acceptance_criteria:
    - given: ""                         # precondition / starting state
      when: ""                          # action / trigger
      then: ""                          # expected outcome / observable result

  # ── API Contract ──
  api_contract:
    endpoint: ""                        # e.g. POST /api/v1/orders
    method: ""                          # GET | POST | PUT | DELETE | PATCH
    request_schema: {}                  # JSON Schema for request body
    response_schema: {}                 # JSON Schema for response body
    error_codes: []                     # expected error codes and their meanings

  # ── Data Model (optional) ──
  data_model:
    entities: []
    # - name: ""
    #   fields:
    #     - name: ""
    #       type: ""
    #       constraints: ""

  # ── Eval Gates ──
  eval_gates:
    - type: "unit_test" | "integration_test" | "e2e" | "performance" | "security"
      criteria: ""                     # what is being measured
      threshold: ""                    # pass/fail boundary (e.g. "> 80% coverage", "< 200ms p95")
      blocking: true                   # if true, gate failure blocks ship

  # ── Constraints ──
  constraints:
    - ""                               # technical, business, or regulatory constraints

  # ── Non-Goals ──
  non_goals:
    - ""                               # explicitly out of scope

  # ── Dependencies ──
  depends_on:
    specs: []                          # other spec IDs this depends on
    services: []                       # upstream services
    data: []                           # required data sources

  # ── Meta ──
  version: "0.1.0"
  status: "draft" | "reviewing" | "approved" | "implementing" | "done"
  created: ""                          # ISO 8601
  updated: ""                          # ISO 8601
```

---

## 2. Workflow

```
┌──────────┐     ┌─────────────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────┐
│  Spec    │────▶│ Auto-Generate   │────▶│  Implement   │────▶│  Eval Gates  │────▶│ Ship  │
│ Written  │     │ Scaffold        │     │  Logic       │     │  Pass        │     │       │
└──────────┘     └─────────────────┘     └──────────────┘     └──────────────┘     └───────┘
                       │                                              │
                       ▼                                              ▼
              - test file(s) from                         gate failure → back
                acceptance_criteria                       to implement step
              - type defs from
                api_contract + data_model
              - stub implementation
              - route registration
              - eval gate configs
```

### Step Details

| Step | Trigger | Agent Action | Output |
|------|---------|-------------|--------|
| **1. Spec Written** | User provides PRD / requirement | Agent converts natural language into YAML spec template, prompts user to fill gaps (outcome, eval gates MUST be explicit) | `specs/<FEAT-XXX>.yaml` |
| **2. Scaffold** | Spec approved (status → `approved`) | Agent reads spec → generates test file from acceptance_criteria, type definitions from api_contract+data_model, stub implementation, and eval gate configs | test file, types file, stub impl |
| **3. Implement** | Scaffold exists | Agent fills implementation logic; test-driven: write code until eval gates pass | working implementation |
| **4. Eval Gates** | Implementation complete | Agent runs all eval gates; any blocking gate failure returns to step 3 | gate results (pass/fail) |
| **5. Ship** | All blocking eval gates pass | Merge PR, update spec status → `done`, link to release | merged code |

---

## 3. Agent Consumption Rules

### How an agent reads and executes against a spec:

```yaml
agent_consumption:
  # Step 1: Parse spec YAML
  parse:
    action: "Read spec file as structured YAML"
    output: "spec object with all fields resolved"

  # Step 2: Generate test file from acceptance_criteria
  generate_tests:
    for_each: "spec.acceptance_criteria"
    template: |
      describe("{spec.id} - {ac.given}", () => {{
        it("should {ac.then} when {ac.when}", async () => {{
          // Arrange: {ac.given}
          // Act: {ac.when}
          // Assert: {ac.then}
        }});
      }});
    output_file: "tests/{spec.id}_acceptance.test.ts"

  # Step 3: Generate type definitions from api_contract + data_model
  generate_types:
    from: "spec.api_contract"
    template: |
      // Request type
      type {Entity}Request = {request_schema → TypeScript interface}
      // Response type
      type {Entity}Response = {response_schema → TypeScript interface}
    from_data_model: "spec.data_model"
    template: |
      interface {entity.name} {{
        {entity.fields → TypeScript properties}
      }}
    output_file: "src/types/{spec.id}.ts"

  # Step 4: Generate stub implementation
  generate_stub:
    from: "spec.api_contract + spec.data_model"
    template: |
      export async function {handlerName}(req: {Entity}Request): Promise<{Entity}Response> {{
        // TODO: Implement business logic for {spec.id}
        throw new Error("Not implemented");
      }}
    output_file: "src/handlers/{spec.id}.ts"

  # Step 5: Generate eval gate configs
  generate_eval_config:
    from: "spec.eval_gates"
    template: |
      {gate.type}: {gate.criteria} → threshold: {gate.threshold}
    output_file: "eval/{spec.id}.config.yaml"

  # Step 6: Register route (if api_contract exists)
  register_route:
    if: "spec.api_contract"
    action: "Add route entry to router config using endpoint + method + handler reference"
```

### Consumption constraints:
- Agent MUST NOT skip any eval gate marked `blocking: true`
- Agent MUST generate tests BEFORE implementation (TDD order)
- If `depends_on.specs` is non-empty, agent MUST verify dependent specs are `done` before starting
- Agent SHOULD use existing project conventions (test framework, type system, file structure) when generating scaffold

---

## 4. Validation Rules

A spec is **invalid** and MUST be rejected at the gate if ANY of the following are missing or empty:

| # | Rule | Severity | Description |
|---|------|----------|-------------|
| V1 | `outcome` is empty or not measurable | **BLOCKING** | Outcome must describe a specific, observable, measurable result. "Improve performance" is invalid; "p95 latency < 200ms" is valid. |
| V2 | `acceptance_criteria` is empty or lacks given/when/then | **BLOCKING** | Minimum 1 AC with all three BDD fields populated. |
| V3 | `eval_gates` is empty or has no blocking gate | **BLOCKING** | At least one eval gate must exist with `blocking: true`. No gate = no way to know if feature works. |
| V4 | `api_contract` exists but lacks `error_codes` | **WARNING** | API endpoints should define expected error codes. |
| V5 | `owner` is empty or "TBD" | **BLOCKING** | Every spec has exactly one accountable person. |
| V6 | Spec ID is not unique | **BLOCKING** | Duplicate spec IDs are rejected. |
| V7 | `version` not in semver format | **WARNING** | Spec version should follow semver (0.1.0, 1.0.0, etc.). |
| V8 | Dependent specs (`depends_on.specs`) not found or not `done` | **BLOCKING** | Cannot start a spec that depends on incomplete work. |

### Validation execution:
```
agent reads spec → runs validator → if BLOCKING violations exist → reject, return error list → agent requests user to fix
                                 → if only WARNING violations → proceed with caveat logged
                                 → if clean → proceed to scaffold generation
```

---

## 5. Integration with Existing Tools

### Jira Integration
```
spec.id: "FEAT-001"
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ Agent creates Jira task(s) from spec:                │
│                                                      │
│ - Epic/Story: spec.title + spec.problem_statement    │
│ - Subtasks: one per acceptance_criteria              │
│ - Custom fields: spec.outcome → description          │
│ - Link: Jira issue ↔ spec file (remote issue link)   │
│ - Status sync: spec.status ↔ Jira status             │
│                                                      │
│ jira_create_issue(                                   │
│   project_key="<project>",                           │
│   summary=spec.title,                                │
│   description=spec.outcome + spec.problem_statement, │
│   issue_type="Story"                                 │
│ )                                                    │
└──────────────────────────────────────────────────────┘
```

### GitLab Integration
```
spec.id: "FEAT-001"
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ Agent creates feature branch from spec:              │
│                                                      │
│ - Branch name: feat/{spec.id}-{slug-title}           │
│ - Base: develop (default)                            │
│ - MR template: pre-filled with spec content          │
│ - MR description: spec.outcome + acceptance_criteria │
│ - MR labels: auto-applied from spec                  │
│                                                      │
│ Branch: feat/FEAT-001-user-auth                      │
│ MR title: [FEAT-001] {spec.title}                    │
└──────────────────────────────────────────────────────┘
```

### Knowledge Graph Integration
```
Agent submits spec as a KG delta after approval:

kg_submit_delta({
  nodes: [
    { label: "FeatureSpec", name: spec.id, properties: spec }
  ],
  relationships: [
    { from: spec.id, to: spec.depends_on.specs, type: "DEPENDS_ON" },
    { from: spec.id, to: spec.depends_on.services, type: "CALLS" },
    { from: spec.id, to: spec.owner, type: "OWNED_BY" }
  ]
})
```

### Test-Agent Integration
```
Agent consuming spec for test generation:

1. Read spec → extract acceptance_criteria
2. For each AC:
   - Map given/when/then → test framework assertions
   - Generate test fixture data from api_contract.request_schema
   - Wire up mock/stub from depends_on.services
3. Generate eval gate runner that:
   - Reads spec.eval_gates
   - Runs associated test suites
   - Reports pass/fail per gate with threshold comparison
4. Output: test file + CI gate config
```

---

## 6. Spec Lifecycle State Machine

```
  ┌────────┐    approve    ┌───────────┐    scaffold_ok    ┌──────────────┐
  │ draft  │──────────────▶│ approved  │──────────────────▶│ implementing │
  └────────┘               └───────────┘                   └──────┬───────┘
       ▲                        │                                │
       │     request_changes    │         gate_failure           │
       └────────────────────────┘    ◄───────────────────────────┘
                                                            │
                                                     all blocking
                                                     gates pass
                                                            │
                                                            ▼
                                                     ┌────────┐
                                                     │  done  │
                                                     └────────┘
```

State transitions are enforced:
- `draft → approved`: requires human review gate; outcome + AC + eval gates must pass validation
- `approved → implementing`: agent generates scaffold, verified by scaffold integrity check
- `implementing → done`: all blocking eval gates must pass
- `implementing → approved`: gate failure triggers rollback for rework
- Any state → `draft`: on `request_changes` (re-review triggered)

---

## 7. Example: Complete Spec

```yaml
spec:
  id: "FEAT-042"
  title: "User Email Verification on Registration"
  outcome: "95% of new users complete email verification within 5 minutes of registration; verification API p95 latency < 500ms"
  owner: "zhangsan"

  problem_statement: "Fake accounts are polluting the system. Email verification reduces spam accounts by requiring a valid email before granting full access."
  user_story: "As a platform admin, I want new users to verify their email so that only legitimate accounts can access the system."

  acceptance_criteria:
    - given: "a user has just submitted registration"
      when: "the registration is successful"
      then: "a verification email is sent to the registered address within 10 seconds"

    - given: "a user has received a verification email"
      when: "the user clicks the verification link"
      then: "the user's account status changes to 'verified' and they are redirected to the dashboard"

    - given: "a user has a verified account"
      when: "the user attempts to register again with the same email"
      then: "the system returns a 409 Conflict with message 'Email already registered'"

  api_contract:
    endpoint: "/api/v1/auth/verify-email"
    method: "POST"
    request_schema:
      type: "object"
      required: ["token"]
      properties:
        token:
          type: "string"
          description: "Verification token from email link"
    response_schema:
      type: "object"
      properties:
        verified:
          type: "boolean"
        message:
          type: "string"
    error_codes:
      - { code: 400, meaning: "Invalid or expired token" }
      - { code: 409, meaning: "Email already verified" }
      - { code: 500, meaning: "Email service unavailable" }

  data_model:
    entities:
      - name: "EmailVerificationToken"
        fields:
          - { name: "id", type: "UUID", constraints: "PK" }
          - { name: "user_id", type: "UUID", constraints: "FK → users.id" }
          - { name: "token", type: "VARCHAR(256)", constraints: "UNIQUE, NOT NULL" }
          - { name: "expires_at", type: "TIMESTAMP", constraints: "NOT NULL" }
          - { name: "used_at", type: "TIMESTAMP", constraints: "NULLABLE" }

  eval_gates:
    - type: "unit_test"
      criteria: "Verification token generation, validation, and expiry logic"
      threshold: "> 90% line coverage"
      blocking: true
    - type: "integration_test"
      criteria: "Full registration → email send → click verify → account verified flow"
      threshold: "all pass"
      blocking: true
    - type: "performance"
      criteria: "Verification API endpoint latency"
      threshold: "p95 < 500ms, p99 < 1000ms"
      blocking: true
    - type: "security"
      criteria: "Token brute-force resistance, rate limiting on verify endpoint"
      threshold: "max 5 attempts per IP per minute"
      blocking: true

  constraints:
    - "Must use transactional email service (Resend/SES), not SMTP relay"
    - "Verification token expires after 24 hours"
    - "GDPR: do not log full email address in verification logs"

  non_goals:
    - "Phone number verification (separate spec FEAT-043)"
    - "Social login (OAuth) verification flow"
    - "Admin manual email verification override"

  depends_on:
    specs: []
    services: ["email-service", "user-service"]
    data: ["users table", "email_verification_tokens table"]

  version: "0.1.0"
  status: "draft"
  created: "2026-05-27T10:00:00+08:00"
  updated: "2026-05-27T10:00:00+08:00"
```

---

## 8. Scaffold Output Convention

After scaffold generation for the example above, the agent produces:

```
src/
├── types/
│   └── FEAT-042.ts                  # TypeScript interfaces from api_contract + data_model
├── handlers/
│   └── FEAT-042.ts                  # Stub: POST /api/v1/auth/verify-email
tests/
├── FEAT-042_acceptance.test.ts      # Tests from acceptance_criteria (BDD)
├── FEAT-042_unit.test.ts            # Unit tests from eval_gates[unit_test]
├── FEAT-042_integration.test.ts     # Integration tests from eval_gates[integration_test]
eval/
├── FEAT-042.config.yaml             # Eval gate thresholds
```

---

## 9. Error Handling

| Scenario | Agent Behavior |
|----------|---------------|
| Spec YAML parse error | Report exact line/column, suggest fix |
| Validation failure (BLOCKING) | List all violations, reject spec, request human fix |
| Scaffold generation failure | Retry once with adjusted template; if still fails, report to owner |
| Eval gate failure | Report which gate failed, actual vs threshold, return to implement step |
| Dependent spec not done | Block progress, list unmet dependencies |
| Duplicate spec ID | Reject with conflict report |
