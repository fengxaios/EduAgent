# 青年开源种子计划 · 申报表

## 一、项目基本信息

| 字段 | 内容 |
|------|------|
| 项目名称 | EduAgent — 面向教学场景的轻量级多智能体分布式框架 |
| 项目地址 | https://github.com/fengxaios/EduAgent |
| GitLink 镜像 | https://gitlink.org.cn/fengxaio/EduAgent |
| 所属赛道 | AI Agent |
| 开源许可 | Apache License 2.0 (OSI 认证) |
| 项目版本 | v1.1.0 |
| 仓库平台 | GitHub + GitLink 双仓库同步 |
| 核心语言 | Python 3.10+ |

## 二、项目简介（300 字以内）

EduAgent 是一个面向教学场景的轻量级多智能体分布式框架，实现 Plan → Execute → Reflect 三阶段 Agent 循环，并在 v2.0 中引入 DAG 并行编排、容错机制与上下文隔离等工程化能力。框架内置 6 个教学专项 Agent（教案设计、习题生成、知识点拆解、图片分析、学习诊断、自动报告），支持智能路由、管线协作和结构化通信协议（PentAGI 启发）。项目不依赖 LangChain 等重型框架，标准 Python 包布局、一键安装。EduAgent 致力于降低 AI Agent 技术在教育领域的应用门槛，让教师和教育从业者能够直接使用多智能体协作完成从教学设计到学习诊断的全流程工作。

## 三、项目创新点

1. **Plan → Execute → Reflect 三阶段 Agent 循环**：每个 Agent 执行任务时经历规划—执行—反思的完整链路，通过启发式策略自动判断是否需要迭代优化，兼顾输出质量和响应效率。

2. **v2.0 分布式编排框架**：引入 DAG（有向无环图）并行调度引擎，支持多 Agent 任务按依赖关系自动并行执行；内置循环检测与守护机制，保证编排安全性；Task 信封协议实现标准化的 Agent 间通信与状态传递。

3. **工程化基础设施（Harness Engineering）**："地图 + 目标 + 验收"三位一体的 Agent 工程规范，每个 Agent 携带 spec 文档和验收标准，从源头保证输出质量可控。

4. **PentAGI 启发的结构化通信协议**：Agent 之间通过标准 JSON 消息（AgentMessage）传递任务、状态和置信度，PipelineReport 自动生成跨 Agent 分析报告，将"管道串行"升级为"可观测协作"。

5. **教育场景深度适配**：6 个 Agent 覆盖教学全链路——教案设计支持 3 档详略模式、习题生成支持 4 档难度分层、知识点拆解强制输出四段（知识树+前置依赖+教学路线+常见误区）、图片分析支持 OCR+公式识别+LaTeX 输出、学习诊断实现学生端个性化反馈闭环。

6. **轻量自研，零框架依赖**：不依赖 LangChain，核心框架精简易读；标准 Python 包布局，`pip install -e .` 一键安装；内置容错机制（重试+降级+超时守护）。

7. **多智能体协作测试方法**：首创「写代码的人不测试，测试的人不写代码」的 Agent 测试原则，7 个 Agent 并行、2 轮迭代、459 项测试 0 失败，形成可复用的多 Agent 协作测试方法论。

## 四、技术方案

### 架构分层
```
┌──────────────────────────────────────────┐
│       Orchestrator (编排层)               │
│  智能路由 + 管线编排 + DAG 并行调度       │
├──────────────────────────────────────────┤
│       Framework v2.0 (分布式框架层)       │
│  AgentRunner │ DAGOrchestrator            │
│  FaultTolerance │ ContextIsolation        │
│  TaskEnvelope │ Automation                │
├──────────────────────────────────────────┤
│       Agents (执行层)                     │
│  LessonPlanner │ QuizGenerator            │
│  KnowledgeMapper │ ImageAnalyzer          │
│  LearningDiagnosisAgent │ ReporterAgent   │
├──────────────────────────────────────────┤
│       Core (核心层)                       │
│  Agent 基类 │ Memory │ ToolRegistry       │
│  StructuredProtocol │ Evaluator           │
├──────────────────────────────────────────┤
│       LLM (模型层)                        │
│  OpenAI SDK ── 通义千问 / DeepSeek        │
└──────────────────────────────────────────┘
```

### 技术栈
- **语言**：Python 3.10+
- **LLM SDK**：OpenAI SDK（兼容任何 OpenAI API 服务）
- **默认模型**：阿里云百炼 qwen-plus / DeepSeek
- **Web UI**：Gradio
- **可视化 LLM**：base64 编码图片接入
- **构建工具**：setuptools + pyproject.toml
- **测试框架**：pytest（65 项自动化测试：34 单元测试 + 31 边界用例）

### 关键技术决策
- 自研 Agent 框架而非依赖 LangChain，保证轻量和透明
- src/ 标准包布局，符合 Python 社区最佳实践
- v2.0 引入 DAG 并行编排，将线性管线升级为依赖驱动的并行执行
- 结构化通信协议解耦 Agent 间耦合，支持可观测多 Agent 协作
- 容错机制内置：重试策略 + 优雅降级 + 超时守护
- 上下文隔离设计：每个 Agent 独立上下文窗口，防止噪声累积

## 五、项目进展

### 已实现（v1.1.0）

**核心框架**
- ✅ Agent 基类：Plan → Execute → Reflect 完整循环
- ✅ 多 Agent 编排器：智能路由 + 管线协作（5 Agent 串联）
- ✅ v2.0 分布式编排：DAG 并行调度 + DFS 循环检测 + 守护机制
- ✅ 容错系统：重试策略 + 优雅降级 + 超时守护（负耗时防护）
- ✅ 上下文隔离：每 Agent 独立上下文窗口 + WAL 机制
- ✅ 双通道记忆系统：对话 + 知识库，支持持久化

**教学 Agent（6 个 + CLI）**
- ✅ 教案设计 Agent：3 档详略模式
- ✅ 习题生成 Agent：4 档难度分层
- ✅ 知识点拆解 Agent：四段式输出
- ✅ 图片分析 Agent：OCR + 公式识别 + LaTeX
- ✅ 学习诊断 Agent：7 类错误识别 + 4 级掌握度 + 离线统计分析
- ✅ 自动报告 Agent：PipelineReport 跨 Agent 分析
- ✅ CLI 命令行工具：`eduagent lesson/quiz/map/pipeline/diagnosis` 一键调用

**工程质量**
- ✅ 结构化通信协议：AgentMessage + TaskEnvelope
- ✅ 输出质量评估器（Evaluator）
- ✅ Harness Engineering 实践指南
- ✅ 多智能体协作测试方法论：7 Agent × 2 轮 × 459 测试
- ✅ 65 项自动化测试通过（34 pytest + 31 边界用例）+ 459 项多 Agent 协作测试
- ✅ 6 个 bug 修复（含死代码清理、静默数据丢失、缺失时间戳等）
- ✅ 双语文档（中英文 README + CHANGELOG + CONTRIBUTING + 测试方法论）
- ✅ GitHub Release v0.1.0 / v0.2.0 / v0.2.1 / v1.0.0 / v1.1.0
- ✅ Gradio Web 界面
- ✅ GitLink 镜像已同步

### 代码统计
- Python 源码：~4,600 行（含 v2.0 框架 ~1,500 行）
- 测试体系：65 项自动化测试 + 459 项多 Agent 协作测试（7 Agent × 2 轮）
- 提交历史：21 commits，清晰的版本迭代
- 文档：11 个 Markdown 文档，中英文双语
- 版本迭代：v0.1.0 → v0.2.0 → v0.2.1 → v1.0.0 → v1.1.0

## 六、团队信息

| 字段 | 内容 |
|------|------|
| 项目联系人 | 郑愿 |
| 团队人数 | 1 人（个人项目） |
| 角色 | 项目发起人、核心开发者、维护者 |

## 七、未来规划

### 短期（3 个月）
- 增加对更多 LLM 的原生支持（DeepSeek-V4、本地模型）
- 补全 Agent 间并行协作能力（已实现 DAG 并行基础）
- 发布 PyPI 正式包

### 中期（6 个月）
- 开发 LMS（学习管理系统）集成插件
- 构建教学知识图谱引擎
- 社区建设：吸引教育技术开发者贡献
- 探索 MXMACA 国产算力适配

### 长期目标
- 成为教育领域 AI Agent 基础设施
- 赋能一线教师零代码使用多 Agent 完成教学全流程
- 深度融入国产 AI 算力生态（通义千问/DeepSeek/沐曦 GPU 适配）

## 八、补充材料

- GitHub：https://github.com/fengxaios/EduAgent
- GitLink 镜像：https://gitlink.org.cn/fengxaio/EduAgent
- 项目演示（Gradio UI 截图见附件）
- 管线实验报告：见 `pipeline_report_demo.md` + `pipeline_report_newton.md`
- Harness Engineering 实践：见 `docs/HARNESS_ENGINEERING_GUIDE.md`
- 多智能体测试方法论：见 `docs/MULTI_AGENT_TESTING.md`
- v2.0 框架演示：见 `examples/framework_demo.py`
- API 文档：见 README.md

---

> 申报人：郑愿  
> 版本：v1.1.0  
> 日期：2026年7月12日
