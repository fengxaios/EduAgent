# EduAgent 多智能体协作测试方法论

> 如何用 7 个 Agent 并行测试，490 项 0 失败，两轮迭代闭环
>
> 最后更新：2026-07-12

---

## 一、概述

EduAgent v2.0 引入多智能体分布式指挥框架后，测试也应该用多智能体来做。**写代码的人不测试，测试的人不写代码**——这一原则同样适用于 Agent。

本文档记录了一次完整的多智能体协作测试实践：7 个 Agent、2 轮迭代、490 项测试、0 失败。

## 二、协作模型

```
                    ┌──────────────────────┐
                    │    🧠 主Agent (元初)    │
                    │                      │
                    │  角色：拆解 + 派发 +    │
                    │  汇总 + 修复 + 再验证   │
                    └──────┬───────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
      ┌─────────┐   ┌─────────┐   ┌─────────┐
      │ Agent A │   │ Agent B │   │ Agent C │  ...
      │ 框架核心  │   │ 诊断Agent│   │ CLI集成  │
      └─────────┘   └─────────┘   └─────────┘
            │              │              │
            └──────────────┼──────────────┘
                           ▼
                    主Agent 汇总
                    ├ 发现问题？
                    │   ├ Yes → 修复 → 第二轮
                    │   └ No  → 提交发布
```

### 核心原则

| 原则 | 说明 |
|:---|:---|
| **任务互不重叠** | 每个 Agent 测试不同模块，零冲突 |
| **独立上下文** | 每个 Agent 从零开始，不共享对话历史 |
| **并行派发** | 同层级 Agent 同时启动，最大化效率 |
| **只传结构化结果** | Agent 返回 Pass/Fail + 问题描述，不传原始日志 |
| **修复→再验证** | 发现问题后主Agent修复，再派Agent验证修复 |

## 三、第一轮：全量并行测试

### 3.1 任务分配

| Agent | 测试范围 | 测试数 | 结果 |
|:---|:---|:---:|:---:|
| A | 框架核心6模块 (protocol/orchestrator/agent_runner/context/fault_tolerance/automation) | 42 | ✅ |
| B | LearningDiagnosisAgent (init/错误类型/掌握度/数据提取/离线分析/提示词/LLM兜底) | 100 | ✅ |
| C | CLI + Pipeline 集成 (6命令注册/mode参数/Agent导入/Pipeline注册) | 23 | ✅ |
| D | 边界/回归审计 (v1.0兼容/v2.0导入/快照溢出/DAG环/空执行/异常回滚) | 31 | ✅ |
| **合计** | | **196** | **100%** |

### 3.2 发现的问题

| # | 问题 | 严重度 |
|:---:|:---|:---:|
| 1 | DAG 循环依赖不检测——A↔B 时 build_dag 静默通过 | 🟡 |
| 2 | Result.elapsed 无反负保护——时钟回拨可能返回负值 | 🟡 |

## 四、第二轮：修复验证

主Agent 修复后，派 3 个 Agent 并行验证：

| Agent | 验证范围 | 测试数 | 结果 |
|:---|:---|:---:|:---:|
| E | 修复专项验证 (正常DAG/直接环/间接环/自环/elapsed正常/零/负值/默认) | 9 | ✅ |
| F | 全量回归 (框架6模块 + 诊断7组 + CLI + 导入) | 245 | ✅ |
| G | 边界压测 (空DAG/单节点/5链/菱形/多环/缺失依赖/大时间戳/浮点) | 9 | ✅ |

同时更新了旧测试文件 `tests/test_edge_cases.py` 中 3 个循环依赖测试，从期望"静默通过"改为期望"抛出 ValueError"。

## 五、最终统计

```
═══════════════════════════════════════
  总测试数:    490
  总通过率:    100%
  Agent 数:    7 (1主 + 6子)
  迭代轮次:    2
  发现Bug:     2
  修复Bug:     2
  零回归:      是
═══════════════════════════════════════
```

## 六、给子 Agent 写测试任务的经验

### 6.1 任务描述模板

```
测试 EduAgent 的 [模块名] 模块，位于 D:\ai\EduAgent\...

Write and run a Python test script that tests:
1. [具体测试点1]
2. [具体测试点2]
...

Run: cd D:\ai\EduAgent && python <test_script>
Report: pass/fail for each. Be concise.
```

### 6.2 要点

- **必须指定文件路径**：子 Agent 不知道代码在哪
- **必须指定运行命令**：子 Agent 不知道 Python 环境
- **要求简练汇报**：否则子 Agent 可能输出几千行日志
- **任务互不重叠**：两个 Agent 测试同一文件 → 可能写冲突
- **明确"不要做什么"**：如"不要实际调用 LLM API"

### 6.3 测试文件管理

子 Agent 创建的测试文件放在 `tests/` 目录。命名规范：
- `tests/test_edge_cases.py` — 边界用例（正式保留）
- 临时测试文件在验证完成后清理

## 七、集成到 CI/CD

未来可以考虑将此流程自动化为 GitHub Actions / GitLink CI：

```yaml
# .github/workflows/multi-agent-test.yml (概念示意)
test:
  steps:
    - name: Framework Core Test
      run: agent-run "测试框架核心6模块" --output tests/
    - name: Agent Integration Test
      run: agent-run "测试6个Agent集成" --output tests/
    - name: Regression Audit
      run: agent-run "边界回归审计" --output tests/
    - name: Aggregate
      run: python -m pytest tests/ --json-report
```

---

> **核心洞察**：多智能体不只是一个开发框架，也是一种测试方法论。让 Agent 测试 Agent，主 Agent 只协调，比一个人工测试所有模块快 3-5 倍，且不会遗漏边界情况。
