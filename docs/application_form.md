# 青年开源种子计划 · 申报表

## 一、项目基本信息

| 字段 | 内容 |
|------|------|
| 项目名称 | EduAgent — 面向教学场景的轻量级多智能体框架 |
| 项目地址 | https://github.com/fengxaios/EduAgent |
| 所属赛道 | AI Agent |
| 开源许可 | Apache License 2.0 (OSI 认证) |
| 项目版本 | v0.2.1 |
| 仓库平台 | GitHub + GitLink 镜像 |
| 核心语言 | Python 3.10+ |

## 二、项目简介（300 字以内）

EduAgent 是一个面向教学场景的轻量级多智能体框架，实现 Plan → Execute → Reflect 三阶段 Agent 循环。框架内置 5 个教学专项 Agent（教案设计、习题生成、知识点拆解、图片分析、自动报告），支持智能路由、管线协作和结构化通信协议（PentAGI 启发）。项目不依赖 LangChain 等重型框架，核心代码精简易扩展，通过 `pip install -e .` 一键安装。EduAgent 致力于降低 AI Agent 技术在教育领域的应用门槛，让教师和教育从业者能够直接使用多智能体协作完成从教学设计到内容生成的全流程工作。

## 三、项目创新点

1. **Plan → Execute → Reflect 三阶段 Agent 循环**：每个 Agent 执行任务时经历规划—执行—反思的完整链路，通过启发式策略自动判断是否需要迭代优化，兼顾输出质量和响应效率。

2. **PentAGI 启发的结构化通信协议**：Agent 之间通过标准 JSON 消息（AgentMessage）传递任务、状态和置信度，PipelineReport 自动生成跨 Agent 分析报告，将"管道串行"升级为"可观测协作"。

3. **教育场景深度适配**：5 个 Agent 覆盖教学核心场景——教案设计支持 3 档详略模式、习题生成支持 4 档难度分层、知识点拆解强制输出四段（知识树+前置依赖+教学路线+常见误区）、图片分析支持 OCR+公式识别+LaTeX 输出。

4. **轻量自研，零框架依赖**：不依赖 LangChain，核心框架 < 500 行，评审可直接阅读全部源码；标准 Python 包布局，`pip install -e .` 一键安装。

5. **双通道记忆系统**：对话上下文记忆 + 结构化知识库，支持持久化存储和关键词检索，Agent 可以跨会话保持教学知识。

## 四、技术方案

### 架构分层
```
┌─────────────────────────────────────┐
│         Orchestrator (编排层)        │
│   智能路由 + 管线编排 + 状态管理     │
├─────────────────────────────────────┤
│  Agents (执行层)                      │
│  LessonPlanner │ QuizGenerator       │
│  KnowledgeMapper │ ImageAnalyzer     │
│  ReporterAgent                       │
├─────────────────────────────────────┤
│  Core (核心层)                        │
│  Agent 基类 │ Memory │ ToolRegistry  │
│  StructuredProtocol │ Evaluator      │
├─────────────────────────────────────┤
│  LLM (模型层)                         │
│  OpenAI SDK ── 通义千问 / DeepSeek   │
└─────────────────────────────────────┘
```

### 技术栈
- **语言**：Python 3.10+
- **LLM SDK**：OpenAI SDK（兼容任何 OpenAI API 服务）
- **默认模型**：阿里云百炼 qwen-plus
- **Web UI**：Gradio
- **可视化 LLM**：base64 编码图片接入
- **构建工具**：setuptools + pyproject.toml

### 关键技术决策
- 自研 Agent 框架而非依赖 LangChain，保证轻量和透明
- src/ 标准包布局，符合 Python 社区最佳实践
- .env 自动发现从包位置向上查找，无需手动配置路径
- 结构化通信协议解耦 Agent 间耦合，支持可观测多 Agent 协作

## 五、项目进展

### 已实现（v0.2.1）
- ✅ Agent 基类：Plan → Execute → Reflect 完整循环
- ✅ 多 Agent 编排器：智能路由 + 管线协作
- ✅ 双通道记忆系统：对话 + 知识库，支持持久化
- ✅ 工具注册系统：OpenAI Function Calling 集成
- ✅ 5 个教学 Agent：教案 / 习题 / 知识拆解 / 图片分析 / 自动报告
- ✅ 结构化通信协议：AgentMessage + PipelineReport
- ✅ 输出质量评估器（Evaluator）
- ✅ 输出模式控制（brief/standard/detailed）+ 难度分层（basic/intermediate/advanced/all）
- ✅ 多模态支持：Vision LLM + 图片 OCR/公式识别
- ✅ 标准 Python 包：pip install -e . 一键安装
- ✅ 34+ 单元测试
- ✅ 双语文档（中英文 README + CHANGELOG）
- ✅ GitHub Release v0.1.0 / v0.2.0 / v0.2.1
- ✅ Gradio Web 界面
- ✅ GitLink 镜像准备

### 代码统计
- Python 源码：~1,400 行
- 单元测试：34+ 个，覆盖核心路径
- 提交历史：10+ commits，清晰的版本迭代

## 六、团队信息

| 字段 | 内容 |
|------|------|
| 项目联系人 | 郑愿 |
| 团队人数 | 1 人（个人项目） |
| 角色 | 项目发起人、核心开发者、维护者 |

## 七、未来规划

### 短期（3 个月）
- 增加对更多 LLM 的原生支持（DeepSeek、本地模型）
- 补全 Agent 间并行协作能力
- 发布 PyPI 正式包

### 中期（6 个月）
- 开发 LMS（学习管理系统）集成插件
- 构建教学知识图谱引擎
- 社区建设：吸引教育技术开发者贡献

### 长期目标
- 成为教育领域 AI Agent 基础设施
- 赋能一线教师零代码使用多 Agent 完成教学全流程
- 深度融入国产 AI 算力生态（通义千问/DeepSeek 适配）

## 八、补充材料

- GitHub：https://github.com/fengxaios/EduAgent
- 项目演示（Gradio UI 截图见附件）
- 管线实验报告：见 `examples/pipeline_experiment.py` + `protocol_comparison.md`
- API 文档：见 README.md

---

> 申报人：郑愿  
> 日期：2026年7月10日
