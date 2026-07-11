# EduAgent Harness Engineering 实践指南

> 让 AI Agent 长时间自主工作不拉胯的工程方法论
>
> 基于费曼学徒冬瓜《Agent Loop: 多智能体协同》视频 + Anthropic/OpenAI 生产实践
> 最后更新：2026-07-12

---

## 目录

1. [什么是 Harness Engineering](#1-什么是-harness-engineering)
2. [核心公式：Agent = Model + Harness](#2-核心公式agent--model--harness)
3. [三大方案对比](#3-三大方案对比)
4. [多智能体协同架构](#4-多智能体协同架构)
5. [EduAgent v2.0 实操指南](#5-eduagent-v20-实操指南)
6. [上下文焦虑与对策](#6-上下文焦虑与对策)
7. [经验库：让 Agent 越做越好](#7-经验库让-agent-越做越好)
8. [行动清单](#8-行动清单)
9. [附录：生产级参考](#9-附录生产级参考)

---

## 1. 什么是 Harness Engineering

**一句话定义**：Harness Engineering（线束工程）是设计环境、约束、反馈循环和基础设施，使 AI Agent 在规模化场景下可靠运行的工程学科。

```
你不是模型 → 那你就是 Harness
```

Harness 就是**模型之外的一切**：

| 层级 | 解决的核心问题 | 关注点 |
|:---|:---|:---|
| Prompt Engineering | 表达——怎么写好指令 | 让模型听懂意图 |
| Context Engineering | 信息——给 Agent 看什么 | 在正确时机给正确信息 |
| **Harness Engineering** | **执行——系统怎么防崩、怎么持续运转** | **长链路任务的持续正确性** |

### 为什么 Harness 是瓶颈而不是模型？

> "同一个模型只换了接口格式，分数从 6.7% 跳到 68.3%"
> "上下文用到 40% 时 Agent 就开始变蠢"

- 模型能力是上限，Harness 决定你能多接近这个上限
- 长链路任务中，90% 的失败来自 Harness 层面（状态丢失、上下文漂移、缺少回滚）
- 好的 Harness 能让同一个模型的表现提升 10 倍

---

## 2. 核心公式：Agent = Model + Harness

```
┌─────────────────────────────────────────────┐
│                  Agent                       │
│  ┌──────────────┐  ┌──────────────────────┐ │
│  │    Model     │  │      Harness          │ │
│  │  (LLM推理)    │  │  ┌────────────────┐  │ │
│  │              │  │  │ 系统提示词       │  │ │
│  │  能力来源     │  │  │ 工具调用         │  │ │
│  │  不持有状态   │  │  │ 文件系统         │  │ │
│  │              │  │  │ 沙箱/隔离         │  │ │
│  └──────────────┘  │  │ 编排逻辑         │  │ │
│                     │  │ 钩子/中间件       │  │ │
│                     │  │ 反馈回路         │  │ │
│                     │  │ 约束/安全         │  │ │
│                     │  └────────────────┘  │ │
│                     └──────────────────────┘ │
└─────────────────────────────────────────────┘
```

**EduAgent 中的对应**：

| Harness 组件 | EduAgent 实现 |
|:---|:---|
| 系统提示词 | `Agent.get_system_prompt()` |
| 工具调用 | `core.tools.ToolRegistry` |
| 文件系统 | 工作区 `outputs/` + 产物追踪 |
| 编排逻辑 | `DAGOrchestrator` (v2.0) / `Orchestrator` (v1.0) |
| 反馈回路 | `AcceptanceCriteria` + `_validate()` |
| 约束/安全 | `CircuitBreaker` + `RetryPolicy` |
| 状态管理 | `ContextManager` + WAL |

---

## 3. 三大方案对比

### 方案 A：单会话硬撑 ❌

```
一个 Claude 会话一直聊 → token 窗口满 → 上下文焦虑 → 草草收尾
```

- 问题：token 窗口有限，长任务必然溢出
- 症状：模型变得犹豫、提前结束、质量下降
- 适用：5 分钟以内的小任务

### 方案 B：Ralph 方案（while 循环 + 文件系统）🟡

```
while 任务没完成:
    启动新会话
    → 读取文件系统的"待办清单 + 当前状态"
    → 执行一步
    → 更新文件系统（待办、产物、状态）
    → 会话结束
```

- 优点：突破单会话 token 限制，实现简单
- 缺点：每次新会话要重新理解上下文，效率低
- 适用：个人项目、探索性任务

**EduAgent 中的轻量实现**：

```python
async def ralph_loop(task: Task, max_iterations: int = 10):
    """Ralph 式循环：会话 → 执行 → 写文件 → 新会话"""
    state_file = Path(f"outputs/{task.id}_state.json")

    for i in range(max_iterations):
        # 读取上一次的状态
        state = json.loads(state_file.read_text()) if state_file.exists() else {}

        # 执行一步
        agent = create_fresh_agent()
        result = await agent.run(task, context=state)

        # 更新状态文件
        state["iteration"] = i + 1
        state["last_result"] = result
        state["todos"] = result.get("next_steps", [])
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))

        if state["todos"] == []:
            break
```

### 方案 C：多智能体协同 ✅（推荐）

```
主 Agent（只协调）
  ├→ 开发 Agent（独立上下文）
  ├→ 测试 Agent（独立上下文）
  ├→ 审查 Agent（独立上下文）
  └→ 经验库（跨会话持久化）
```

- 优点：上下文隔离、并行执行、角色分明、可扩展
- 缺点：架构复杂度更高
- 适用：生产级项目、团队协作、长时自动化

---

## 4. 多智能体协同架构

### 4.1 核心原则

> "写 bug 的人修 bug，提 bug 的人验收"

| 原则 | 说明 | 反例 |
|:---|:---|:---|
| **上下文隔离** | 每个子 Agent 拥有独立上下文，不共享对话历史 | 所有 Agent 挤一个会话，互相污染 |
| **角色分明** | 开发/测试/审查分离，不越界 | 同一个 Agent 又写代码又审代码 |
| **验收闭环** | 任务下发时带验收标准，执行后自动校验 | 口头说"做好了"就算完 |
| **经验积累** | 每次失败记录到经验库，下次自动避坑 | 同一个坑反复踩 |
| **失败可逆** | 每一步有回滚方案，失败不破坏已有成果 | 一步失败全盘重来 |

### 4.2 EduAgent 中的分工

```
┌─────────────────────────────────────────────┐
│           🧠 DAGOrchestrator (主 Agent)       │
│   只做三件事：                                │
│   1. 拆解需求 → DAG 任务图                    │
│   2. 按层级并行派发 Task                      │
│   3. 收集 Result → 验收 → 重试/回滚           │
├─────────────────────────────────────────────┤
│                                             │
│  Level 0 (并行)                              │
│  ┌──────────┐ ┌────────────┐ ┌───────────┐  │
│  │知识拆解   │ │ PPT生成     │ │ 分镜脚本   │  │
│  │Knowledge  │ │ PPT        │ │ Storyboard │  │
│  └─────┬────┘ └────────────┘ └───────────┘  │
│        │                                     │
│  Level 1 (依赖 Level 0)                      │
│        ▼                                     │
│  ┌──────────┐ ┌────────────┐                │
│  │习题生成   │ │ 学情分析    │                │
│  │Exercise  │ │ Reporter   │                │
│  └──────────┘ └────────────┘                │
│        │                                     │
│  Level 2 (依赖 Level 1)                      │
│        ▼                                     │
│  ┌──────────┐                                │
│  │质量审查   │ ← 独立 Agent，不参与创作       │
│  │Evaluator │                                │
│  └──────────┘                                │
└─────────────────────────────────────────────┘
```

---

## 5. EduAgent v2.0 实操指南

### 5.1 快速开始

```python
from eduagent.framework import (
    DAGOrchestrator, Task, AcceptanceCriteria,
    AgentRunner, RetryPolicy, CircuitBreaker,
    WorkflowEngine, CronScheduler,
)

# 1. 创建调度器
orch = DAGOrchestrator()

# 2. 注册 v1.0 Agent（一行升级）
from eduagent.agents import LessonPlanner, QuizGenerator, Reporter
orch.register_v1(LessonPlanner(), "lesson")
orch.register_v1(QuizGenerator(), "quiz")
orch.register_v1(Reporter(), "report")

# 3. 构建任务 DAG
tasks = [
    Task(
        id="lesson-1",
        type="lesson",
        payload={"topic": "微积分入门", "grade": "大一"},
        criteria=AcceptanceCriteria(checks=[
            "至少包含5个知识点",
            "每个知识点有15分钟课时设计",
            "输出为结构化 JSON",
        ]),
        depends_on=[],  # Level 0，无依赖
    ),
    Task(
        id="quiz-1",
        type="quiz",
        payload={"topic": "微积分入门", "count": 10},
        criteria=AcceptanceCriteria(checks=[
            "至少10道题",
            "覆盖选择题+计算题",
            "每道题标注难度",
        ]),
        depends_on=["lesson-1"],  # Level 1，依赖知识点
    ),
    Task(
        id="report-1",
        type="report",
        payload={"format": "markdown"},
        depends_on=["lesson-1", "quiz-1"],  # Level 2，依赖两者
    ),
]

# 4. 执行
results = await orch.run_dag(tasks)

# 5. 查看结果
for tid, r in results.items():
    print(f"{'✅' if r.ok else '❌'} [{tid}] {r.status.value} | {r.elapsed:.1f}s")
```

### 5.2 加容错保护

```python
# 用熔断器保护 LLM API 调用
api_breaker = CircuitBreaker(
    name="dashscope",
    failure_threshold=5,
    recovery_timeout=30,
)

# 用重试策略包裹不稳定的操作
retry = RetryPolicy(max_retries=3, base_delay=1.0)

@api_breaker.protect
async def safe_llm_call(prompt: str) -> str:
    return await retry.execute(
        llm_client.chat, prompt, task_id="llm-call"
    )
```

### 5.3 定时自动化

```python
scheduler = CronScheduler()

# 每天 21:00 自动整理教学素材
async def daily_material_curation():
    orch = DAGOrchestrator()
    orch.register_v1(KnowledgeMapper(), "knowledge")
    result = await orch.run("整理今天收集的教学素材")

scheduler.add("素材整理", "0 21 * * *", daily_material_curation)

# 每 4 小时检查 Agent 健康状态
async def health_check():
    return {"agents": len(orch.executor._agents), "context_version": orch.context._state.version}

scheduler.add("健康检查", "4h", health_check)
```

### 5.4 创建新 Agent（v2.0 原生）

```python
class GradingAgent(AgentRunner):
    """批改作业 Agent"""

    def __init__(self):
        super().__init__(
            name="GradingAgent",
            agent_type="grading",
            timeout=120,  # 2分钟超时
        )

    async def _execute(self, task: Task) -> dict:
        # 从上游获取学生答案
        quiz_result = task.context.get("quiz", {})
        student_answers = task.payload.get("answers", [])

        # 业务逻辑...
        scores = []
        for answer in student_answers:
            # 批改逻辑
            scores.append({"question": answer["id"], "score": 85, "feedback": "..."})

        return {"scores": scores, "average": sum(s["score"] for s in scores) / len(scores)}

    def _validate(self, result_data: dict, criteria: AcceptanceCriteria) -> bool:
        """验收：所有学生都批改完了吗"""
        scores = result_data.get("scores", [])
        return len(scores) > 0 and all("score" in s for s in scores)
```

---

## 6. 上下文焦虑与对策

### 6.1 什么是上下文焦虑？

Anthropic 发现 Sonnet 4.5 在 token 窗口快满时会：
- 变得犹豫不决
- 倾向于提前收工（哪怕任务没做完）
- 输出质量显著下降

**量化数据**：上下文利用率超过 40% 时 Agent 就开始变蠢。

### 6.2 四种对策

| 策略 | 做法 | 适用场景 |
|:---|:---|:---|
| **压缩（Compact）** | 把历史对话摘要压缩 | token 50-80% 时触发 |
| **上下文重置（Context Reset）** | 启动干净新 Agent，传结构化交接文档 | token > 80% 时 |
| **子代理隔离** | 重活交给子 Agent，只收回结果 | 任何时候（主动策略） |
| **增量执行** | 一个大任务拆成多个小任务，逐步完成 | 长链路任务 |

### 6.3 EduAgent 实现

```python
class ContextGuard:
    """上下文守护 — 监控 token 使用，自动触发保护"""

    def __init__(self, warning_threshold: float = 0.4, critical_threshold: float = 0.8):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def check(self, token_usage: float) -> str:
        """
        返回: "ok" | "compact" | "reset"
        """
        if token_usage < self.warning_threshold:
            return "ok"
        elif token_usage < self.critical_threshold:
            return "compact"  # 触发压缩
        else:
            return "reset"    # 触发上下文重置

    async def context_reset(self, current_state: dict, next_task: Task) -> dict:
        """上下文重置：提取关键状态 → 启动新 Agent → 交班"""
        handoff = {
            "completed": current_state.get("completed", []),
            "pending": current_state.get("pending", []),
            "artifacts": current_state.get("artifacts", []),
            "lessons_learned": current_state.get("lessons", []),
        }
        # 把交接文档注入新 Task 的 context
        next_task.context["handoff"] = handoff
        return handoff
```

---

## 7. 经验库：让 Agent 越做越好

### 7.1 核心思想

> 每次 Agent 犯错 → 不是修完就完了 → 工程化一个方案让它永远不再犯同样的错

Mitchell Hashimoto 的做法：`AGENTS.md` 里的每一行对应一个历史失败案例。

### 7.2 EduAgent 经验库设计

```
outputs/experience/
├── failures.jsonl      # 失败记录（时间戳 + 根因 + 预防规则）
├── successes.jsonl     # 成功模式（什么条件下 Agent 表现好）
├── prompts_changelog/  # 提示词变更历史（每次改 prompt 都记录原因）
└── AGENTS.md           # Agent 启动时自动加载的经验集合
```

### 7.3 失败记录的格式

```json
{
  "timestamp": "2026-07-12T14:30:00+08:00",
  "agent": "QuizGenerator",
  "task_type": "quiz",
  "error_type": "验收失败",
  "root_cause": "习题数量不足，只生成了3道",
  "prevention": "在系统提示词中加入'至少生成10道题'的硬约束",
  "status": "已修复"
}
```

### 7.4 自动注入经验

```python
class ExperienceInjector:
    """在 Agent 执行前，自动注入相关历史经验"""

    def __init__(self, experience_dir: Path = Path("outputs/experience/")):
        self.experience_dir = experience_dir

    def get_relevant_lessons(self, agent_type: str, task_type: str) -> list[str]:
        """查询与当前任务相关的历史教训"""
        lessons = []
        fail_file = self.experience_dir / "failures.jsonl"
        if fail_file.exists():
            for line in fail_file.read_text().splitlines():
                record = json.loads(line)
                if record["agent"] == agent_type or record["task_type"] == task_type:
                    if record.get("status") == "已修复":
                        lessons.append(record["prevention"])
        return lessons

    def inject_into_prompt(self, system_prompt: str, lessons: list[str]) -> str:
        """把经验注入系统提示词"""
        if not lessons:
            return system_prompt
        experience_section = "\n## 历史教训（请严格遵守）\n"
        for i, lesson in enumerate(lessons, 1):
            experience_section += f"{i}. {lesson}\n"
        return system_prompt + experience_section
```

---

## 8. 行动清单

### P0 — 今天就能做

- [x] 把 Agent 注册到 `DAGOrchestrator`，感受并行提速
- [ ] 给每个 Task 加 `AcceptanceCriteria`（哪怕只有一条）
- [ ] 建 `outputs/experience/failures.jsonl`，下次翻车就记一笔

### P1 — 本周完成

- [ ] 拆分一个"开发Agent + 审查Agent"，实现写-验分离
- [ ] 给 LLM API 调用加 `RetryPolicy` + `CircuitBreaker`
- [ ] 写一个 `ContextGuard`，监控 token 使用率

### P2 — 持续建设

- [ ] 建 `AGENTS.md`，每次犯错更新一条经验
- [ ] 用 `CronScheduler` 跑定时自动化任务
- [ ] 建立 Prompt 变更日志（每次改 prompt 都记录原因和效果）

---

## 9. 附录：生产级参考

### Claude Code 的 Agent Loop

Claude Code 的 `queryLoop()` 有 **7+ 个 continue 站点**和**4 级压缩管道**，从 30 行最小实现膨胀到 1800+ 行生产代码。

| 度量指标 | 最小实现 | Claude Code 生产版 |
|:---|:---|:---|
| 代码行数 | 30 | 1800+ |
| Continue 站点 | 1 | 7 |
| 错误恢复路径 | 0 | 5 级联 |
| 压缩策略 | 无 | 4 级管道 |
| 并发模式 | 串行 | 2 种 |

> "生产级 Agent Loop 的复杂性不在于循环本身，而在于循环失败时如何优雅恢复。"

### Anthropic 的 GAN 式三智能体架构

受 GAN（生成对抗网络）思路启发：

```
生成 Agent ──→ 产物 ──→ 评估 Agent ──→ 评分
    ▲                                    │
    └────────── 反馈循环 ────────────────┘
                    +
            审查 Agent（独立验证）
```

- **Context Reset 策略**：上下文快满时不压缩，直接启动干净新 Agent + 结构化交接文档
- **独立评估**：生成和评估由两个 Agent 分别完成，解决自我评价偏差

### Mitchell Hashimoto 的个人 Harness 六步

1. 放弃聊天模式 → 让 Agent 在文件系统+工具环境里干活
2. 复现自己的工作 → 每件事做两遍（自己一遍，Agent 一遍）
3. 下班前启动 Agent → 最后 30 分钟布置长任务
4. 外包确定性任务 → 挑 Agent 一定能做好的事后台跑
5. 工程化 Harness → 每次犯错就加一条防线
6. 始终有 Agent 在跑 → 目标是 10-20% 工作时间有 Agent 后台运行

---

> **最后一条建议**：不要试图一次做到生产级。从 P0 的三个动作开始——并行调度 + 验收清单 + 失败日志。Harness 是长出来的，不是设计出来的。
