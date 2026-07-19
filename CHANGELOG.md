# Changelog

## v2.1.0 (2026-07-19)

### ✨ 新增：多Agent协作模式

- **GroupChat 群聊** — 多个Agent在同一空间讨论/辩论，支持投票达成共识
- **AgentHandoff 交接** — A B C串行交接 / 条件分支 / 广播扇出
- **SharedMemory 共享记忆** — 跨Agent读写持久化记忆，按标签检索

### 🔧 增强

- **ZPD-aware 路由** — 根据学生水平智能分配任务
- **AgentProfile档案** — 结构化能力描述 + 丰富度评分
- **StudentProfile学生画像** — 对话式收集，token级个性化
- **分支管线** — fork-join并行执行支持
- **CLI升级** — 新增 profiles / student / recommend 命令

### 架构

eduagent/
  core/          核心：Agent基类 + 串行编排器
  framework/     框架：DAG调度 + 容错 + 自动化 + 协作模式
  agents/        5个教学专用Agent

## v1.1.0 (2026-07-12)

### 新增
- framework 模块：DAG并行调度、容错系统、自动化
- AgentRunner：Snapshot Execute Verify Rollback 执行循环

## v1.0.0 (2026-07-03)

### 初始发布
- Agent 基类：Plan Execute Reflect 三阶段循环
- 5个教学专用Agent
- 串行管线编排器
- 结构化通信协议
- CLI 命令行接口
