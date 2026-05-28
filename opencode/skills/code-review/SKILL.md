---
name: "code-review"
description: "三轮对抗式 AI 代码审查 — R1 审查员(R1用Claude) → R2 挑战者(Gemini) → R3 裁定者(GPT)，三个模型交叉验证避免认知盲区。触发关键词：提交、commit、push、MR、merge、合并、评审、review"
version: "1.0.0"
author: "linksfield"
---

# 代码审查 — 三轮对抗式 AI 审查

每个 MR 经过三轮对抗式审查，使用不同 AI 模型交叉验证，三个模型互相独立、互相质疑，避免单一模型的认知盲区。模型配置可在「LLM 设置」中调整。

## 三轮流程

| 轮次 | 角色 | 默认模型 | 职责 |
|------|------|----------|------|
| R1 | 审查员 | Claude Sonnet 4 | 逐行审查代码，发现安全、NPE、事务、性能等问题 |
| R2 | 挑战者 | Gemini 3.1 Pro | 使用不同模型逐条质疑 R1 的发现，标记误报/降级/升级/补充遗漏 |
| R3 | 裁定者 | GPT-5.3 Codex | 综合双方证据，给出最终结论、代码证据、建议修改（diff 格式）和评分 |

---

## 严重等级

| 等级 | 含义 | 权重 |
|------|------|------|
| P0 | 必须修复 — 安全漏洞、数据丢失、生产阻断 | 10 分 |
| P1-HIGH | 强烈建议 — NPE、资源泄漏、事务缺失 | 5 分 |
| P1-MED | 建议修复 — 错误处理不当、日志缺失 | 3 分 |
| P1-LOW | 可选修复 — 性能隐患、命名不清晰 | 1 分 |
| P2 | 建议改进 — 代码质量、风格、文档 | 0 分 |

### 评分判定

- **评分 ≥ 10 分** → 需要修改（不可合并）
- **> 0 分且 < 10 分** → 有小问题（需修改后合并）
- **0 分** → 可以合并

---

## 生产环境约束

### MySQL 5.7 约束（P0）

**无论代码目录名是否包含 mysql8，一律按 5.7 审查。违反即 P0。**

禁止使用的 MySQL 8.0+ 语法：
- 窗口函数（ROW_NUMBER, RANK, DENSE_RANK, LEAD, LAG 等）
- CTE（WITH 子句）
- JSON_TABLE
- CREATE INDEX IF NOT EXISTS
- 不可见索引（INVISIBLE INDEX）
- 其他 8.0+ 独有特性

### Java 11 约束（P0）

禁止使用 Java 14+ 特性：
- `record` 类型
- Text Blocks（`"""..."""`）
- Pattern Matching instanceof
- Switch Expressions（`->` 语法）
- Sealed Classes
- 其他 14+ 独有特性

### K8s 约束（P1）

- 禁止依赖本地文件系统持久化
- 配置必须通过 ConfigMap/Secret 注入
- 违反即 P1

---

## R1 审查员 — 审查清单

### P0 审查项（必须修复）

1. SQL/HQL 注入（动态拼接查询）
2. 硬编码密码、API Key、Token
3. 缺少权限校验的 API endpoint
4. IMSI/ICCID 未脱敏（只显示前6后4位）
5. 缺少 @Transactional 的多表写操作
6. 并发场景缺乐观锁/悲观锁
7. 批量操作无分页（OOM 风险）
8. 使用 MySQL 8.0+ 语法
9. 使用 Java 14+ 语法

### P1 审查项（强烈建议）

1. @Transactional 不能用在 private 方法上
2. MyBatis XML 中 `${}` 必须改为 `#{}`
3. @Async 不能在同一个类内调用
4. catch Exception 必须处理或重抛，禁止空 catch
5. 外部系统调用必须有超时 + 重试
6. N+1 查询（循环里调 DB/RPC）
7. 日志必须包含业务上下文，禁止 e.printStackTrace()
8. K8s 环境下依赖本地文件持久化

### IoT MVNO 业务规则

1. 金额计算必须用 BigDecimal，禁止 double/float
2. SIM 状态转换必须校验前置状态
3. MNO 接口必须有幂等性保护
4. 涉及金额的变更必须有审计日志

---

## R2 挑战者 — 质疑清单

对 R1 的每一项发现，用不同模型逐条质疑：

| 裁决 | 含义 |
|------|------|
| **确认 (Confirmed)** | 发现有效，等级评估正确 |
| **误报 (False Positive)** | 发现与代码上下文不符，标记为误报 |
| **降级 (Downgrade)** | 严重等级过高，如 R1 标 P0 实际应为 P1/P2 |
| **升级 (Upgrade)** | 严重等级过低，如 R1 标 P2 实际应为 P0/P1 |
| **补充遗漏 (Missed)** | R1 完全漏掉的问题，这是最危险的 |

---

## R3 裁定者 — 最终裁定

综合 R1 和 R2 的证据：

1. 对每个争议项给出最终裁定
2. 按权重计算总分：P0(10) + P1-HIGH(5) + P1-MED(3) + P1-LOW(1) + P2(0)
3. 输出合并建议
4. 对确认的问题给出建议修改（diff 格式）

---

## 审查执行流程

```
agent 准备提交/审查
     │
     ▼
[1] 读取变更文件列表和 diff
     │
     ▼
[2] R1 审查员 — 逐行审查，输出 findings + summary
     │
     ▼
[3] R2 挑战者 — 质疑 R1，标记误报/降级/升级/补充遗漏
     │
     ▼
[4] R3 裁定者 — 综合裁决，计算评分，输出 merge 建议
     │
     ▼
[5] Gate — 人工决策
     ├── merge: 接受审查结果，继续提交
     ├── fix: 修复 P0/P1 问题后重新审查
     └── abort: 放弃本次提交
```

---

## 输出报告格式

```markdown
# MR Review Report

**Branch**: {branch}
**Base**: {target_branch}
**Date**: {date}
**Files Changed**: {n}

---

## R1 审查员 — 初次审查

| # | 严重等级 | 文件:行号 | 分类 | 问题描述 | 建议修改 |
|---|----------|-----------|------|----------|----------|
| 1 | P0 | Foo.java:42 | SQL注入 | ... | ... |

---

## R2 挑战者 — 质疑结果

| R1 # | 裁决 | 调整后等级 | 理由 |
|------|------|------------|------|
| 1 | 确认 | P0 | ... |
| 2 | 误报 | - | 实际代码已做参数化处理 |

### 补充遗漏

| # | 严重等级 | 文件:行号 | 问题描述 |
|---|----------|-----------|----------|
| 3 | P1-HIGH | Bar.java:88 | N+1 查询 |

---

## R3 裁定者 — 最终裁定

### 确认问题

| # | 等级 | 文件:行号 | 问题 | 建议修改 |
|---|------|-----------|------|----------|
| 1 | P0 | Foo.java:42 | SQL注入 | 改用 #{} 参数化 |
| 3 | P1-HIGH | Bar.java:88 | N+1查询 | 批量查询 |

### 评分

| 等级 | 数量 | 权重 | 小计 |
|------|------|------|------|
| P0 | 1 | ×10 | 10 |
| P1-HIGH | 1 | ×5 | 5 |
| **总分** | | | **15** |

**合并建议**: 不可合并 — 总分 ≥ 10，需修复 P0 问题后重新审查。
```

---

## 提示词版本

| 角色 | Slug | 长度 |
|------|------|------|
| MR Review — Round 3 Arbiter | `mr_review.arbiter` | 3675 chars |
| MR Review — Round 2 Challenger | `mr_review.challenger` | 302 chars |
| MR Review — Custom Rules | `mr_review.custom_rules` | 4628 chars |
| MR Review — Round 1 Reviewer | `mr_review.reviewer` | 3656 chars |

---

## 审查经验与常见漏检模式

> **教训来源**: PR-6450 dual_imsi 迁移，人工审查 10+ 轮后 AI 审查仍发现 3 个 P2 漏检。

### 🔴 审查盲区：聚焦新代码忽略 Diff 全量

**核心问题**: 人工审查倾向于只关注"自己写的代码"，忽略 diff 中其他被修改的既有文件。

**预防策略**:

1. **R1 审查前必须先列出所有变更文件**，逐文件分配审查精力：
   - 新建文件 → 逐行审查
   - 核心修改文件 → 逐行审查
   - 其他变更文件 → 至少检查日志占位符、注释一致性、null 安全

2. **强制检查以下 P2 高频漏检模式**（不依赖运行时，diff 内自证）：

| 模式 | 示例 | 检测方法 |
|------|------|----------|
| 日志占位符与实际参数不匹配 | `log.warn("assetId:{}", contractId)` | grep `log\.(info|warn|error)` 交叉验证 `{}` 数量和参数 |
| 注释与代码不一致 | `// 并行流` 但代码是 `stream()` | grep 中文注释 + 核对下一行代码 |
| copy-paste 残留 | 两处一模一样的代码块但上下文不同 | 对重复代码段做 diff 对比 |

3. **补充遗漏是 R2 最危险的输出** — 每次审查至少追问一次："还有哪些文件被修改了但我没看？"

4. **🔴 修复后必须全量复扫** — 每修复一个问题模式后，用 grep/sed 对**所有修改的文件**（不只是核心文件）再次扫描相同模式。一次修复只覆盖一处，同文件或同 diff 的其他位置大概率还存在相同错误。

   ```
   # 示例：修复日志占位符后，全量复扫
   git diff HEAD~N..HEAD -- '*.java' | grep "log\.\(info\|warn\|error\)" | 逐条校验 {} 与参数匹配
   
   # 示例：修复 orElse(null).get 后，全量复扫
   git diff HEAD~N..HEAD -- '*.java' | grep "orElse(null)\.get"
   
   # 示例：修复 XML foreach 后，全量复扫
   grep -rn "<foreach" 所有 XML | 检查前一行有无 <if> 空守卫
   ```

5. **审查范围 = 全量 diff 文件**，不是"我写的文件"。被波及的既有文件同样需要 P0/P1/P2 扫描。

---

### 🔴 String.split() 边缘情况：分隔符本身作为输入时返回空数组 (P0)

> **教训来源**: PR-6766 sim-service hotfix，修复 `s[1]` 越界后发现 `s[0]` 同样未保护，且同文件另有一处含 `contains("_")` 守卫但仍有相同漏洞。

**核心问题**: Java `String.split(regex)` 的默认行为（limit=0）会丢弃末尾空字符串。当输入字符串**恰好等于分隔符本身**（如 `"_"` 对 `"_"` split）时，结果为空数组 `[]`，而非 `["", ""]`。

```
输入          split("_") 结果    s[0] 结果
"A1_OP"       ["A1","OP"]       ✅ "A1"
"_OP"         ["","OP"]         ✅ ""
"A1_"         ["A1"]            ✅ "A1" (末尾空串被丢弃)
"_"           []                ❌ ArrayIndexOutOfBoundsException
""            []                ❌ ArrayIndexOutOfBoundsException
```

**预防策略**:

1. **修复 split 越界必须同时检查所有数组索引** — 修复 `s[1]` 时，必须连带检查 `s[0]`。split 返回值长度可以是 0、1、2...n，任何不检查的索引都可能在边缘输入下崩溃。

2. **强制检查模式**（不依赖运行时，diff 内自证）：

| 模式 | 检测方法 |
|------|----------|
| `split` 后直接 `[0]` 无长度检查 | grep `\.split\(` → 检查下一行是否有 `length > 0` 或 `length >= 1` |
| `split` 后直接 `[1]` 无长度检查 | grep `\.split\(` → 检查下一行是否有 `length > 1` 或 `length >= 2` |
| `contains("_")` 守卫但未检查 split 结果长度 | 含 `contains` + `split` 的组合需同时检查 split 结果长度 |
| 同文件多处 `split("_")` 模式 | 修复一处后，grep 全文件所有 `split` 模式逐一检查 |

3. **全量复扫命令**：
   ```bash
   # 修复 split 后，全量复扫
   grep -n '\.split(' *.java | while read line; do
     # 检查该行后是否有 length guard
   done
   
   # 快速检测：所有 split 后紧跟数组访问的位置
   grep -A1 '\.split(' *.java | grep '\[' | grep -v 'length'
   ```
