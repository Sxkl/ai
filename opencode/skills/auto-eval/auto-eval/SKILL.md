# Auto-Eval Gate — 自动评估门禁

## 职责

代码生成后自动运行的质量门禁。评分 ≥ 80 自动通过 → 触发 auto-ship。评分 < 80 自动退回 agent 修复。

## 评估维度 (100 分)

| # | 维度 | 满分 | 检查方法 |
|---|------|:---:|------|
| 1 | Lint | 20 | 运行 lint 命令，1 error = -5 |
| 2 | Typecheck | 20 | 编译通过=20，编译失败=0 |
| 3 | Test Pass | 25 | 全部通过=25，1 fail = -5 |
| 4 | Coverage | 15 | ≥80%=15，60-80%=10，<60%=5 |
| 5 | Security | 10 | 无注入/泄露=10，每项=-3 |
| 6 | Complexity | 10 | 新增代码 ≤200行=10，200-400=7，>400=3 |

## 评分决策

```
总分 ≥ 80 → ✅ PASS → 自动触发 auto-ship
总分 60-79 → ⚠️ WARN → 通知 agent 优化后自动重试 1 次
总分 < 60 → ❌ FAIL → 退回 agent，附修复建议
```

## 执行脚本

```bash
# 1. Lint
if [ -f "package.json" ]; then
  npm run lint 2>&1 | tail -5
elif [ -f "build.gradle" ]; then
  ./gradlew checkstyleMain 2>&1 | tail -5
fi

# 2. Typecheck
if [ -f "tsconfig.json" ]; then
  npx tsc --noEmit 2>&1 | tail -5
elif [ -f "build.gradle" ]; then
  ./gradlew compileJava 2>&1 | tail -5
fi

# 3. Test
npm test 2>&1 | tail -10
# or: ./gradlew test

# 4. Coverage (if available)
# npx vitest --coverage
```

## Hive HQ 上报

```bash
# 评估开始
curl -s -X POST http://127.0.0.1:17711/status -H "Content-Type: application/json" -d '{
  "agentId":"auto-eval","status":"working",
  "statusDetail":{"status":"tool_use","toolName":"lint","message":"Auto-Eval: lint 检查中","currentTask":"Eval-{jira_key}"}
}'

# 评估完成
curl -s -X POST http://127.0.0.1:17711/report -H "Content-Type: application/json" -d '{
  "agentId":"auto-eval","type":"task_done",
  "title":"Eval-{jira_key}: {PASS/FAIL} ({score}/100)",
  "summary":"Lint:{l}/20 Type:{t}/20 Test:{p}/25 Cov:{c}/15 Sec:{s}/10 Cpx:{x}/10"
}'
```

## 退回修复格式

当 FAIL 时，生成标准化修复指令：

```markdown
## 🔴 Auto-Eval FAILED — {score}/100

需修复项:
| # | 问题 | 文件 | 建议 |
|---|------|------|------|
| 1 | {issue} | {file}:{line} | {suggestion} |

修复后自动重试 eval。
```
