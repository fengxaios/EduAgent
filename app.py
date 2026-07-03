"""
EduAgent Web Demo — 基于 Gradio 的交互式演示界面

运行: pip install gradio && python app.py
"""

import sys
from pathlib import Path

# 确保项目在 Python 路径中
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

try:
    import gradio as gr
except ImportError:
    print("请先安装 Gradio: pip install gradio")
    sys.exit(1)

from eduagent import (
    Orchestrator,
    LessonPlannerAgent,
    QuizGeneratorAgent,
    KnowledgeMapperAgent,
)

# ─── 初始化 ──────────────────────────────────

orchestrator = Orchestrator()
orchestrator.register_all([
    LessonPlannerAgent(),
    QuizGeneratorAgent(),
    KnowledgeMapperAgent(),
])

AGENT_CHOICES = [
    "auto (智能路由)",
    "lesson_planner (教案设计)",
    "quiz_generator (习题生成)",
    "knowledge_mapper (知识点拆解)",
]

MODE_CHOICES = ["standard (标准)", "brief (精简)", "detailed (详细)"]


# ─── 回调函数 ────────────────────────────────

def run_agent(task: str, agent_choice: str, mode: str, difficulty: str):
    """执行 Agent 并返回结果"""
    if not task.strip():
        return "⚠️ 请输入任务描述", ""

    # 解析参数
    mode_map = {
        "standard (标准)": "standard",
        "brief (精简)": "brief",
        "detailed (详细)": "detailed",
    }
    selected_mode = mode_map.get(mode, "standard")

    try:
        if agent_choice.startswith("auto"):
            # 智能路由
            result = orchestrator.route(task, mode=selected_mode)
            agent_used = result["agent"]
            output = result["result"]
        else:
            # 指定 Agent
            agent_name = agent_choice.split(" ")[0]
            agent = orchestrator.agents[agent_name]

            # 如果是 quiz_generator，注入难度
            if agent_name == "quiz_generator" and difficulty != "default":
                agent.difficulty = difficulty

            output = agent.run(task, mode=selected_mode)
            agent_used = agent_name

        # 统计信息
        stats = f"📊 Agent: {agent_used} | Mode: {selected_mode} | 长度: {len(output)} 字"
        return output, stats

    except Exception as e:
        return f"❌ 执行出错:\n```\n{e}\n```", ""


def run_pipeline(task1: str, task2: str, task3: str):
    """执行管线"""
    pipeline_tasks = []
    if task1.strip():
        pipeline_tasks.append({"agent": "knowledge_mapper", "task": task1})
    if task2.strip():
        pipeline_tasks.append({"agent": "lesson_planner", "task": task2})
    if task3.strip():
        pipeline_tasks.append({"agent": "quiz_generator", "task": task3})

    if not pipeline_tasks:
        return "⚠️ 请至少输入一个任务", ""

    try:
        results = orchestrator.pipeline(pipeline_tasks)
        output_parts = []
        for r in results:
            if "error" in r:
                output_parts.append(f"## ❌ {r['agent']}\n{r['error']}")
            else:
                output_parts.append(f"## ✅ {r['agent']}\n{r['result']}")

        stats = f"📊 Pipeline: {len(pipeline_tasks)} 个 Agent 串行完成"
        return "\n\n---\n\n".join(output_parts), stats
    except Exception as e:
        return f"❌ Pipeline 执行出错:\n```\n{e}\n```", ""


# ─── 界面 ────────────────────────────────────

with gr.Blocks(
    title="EduAgent — AI 教学助手",
    theme=gr.themes.Soft(),
    css="""
    .output-box { font-size: 14px; line-height: 1.6; }
    .stats-box { font-size: 12px; color: #666; }
    """,
) as demo:
    gr.Markdown("""
    # 🧠 EduAgent — AI 教学助手

    面向教学场景的轻量级多智能体框架 | 教案设计 · 习题生成 · 知识点拆解
    """)

    with gr.Tabs():
        # ── 单 Agent 模式 ──
        with gr.TabItem("🎯 单 Agent 执行"):
            with gr.Row():
                with gr.Column(scale=1):
                    agent_choice = gr.Dropdown(
                        label="选择 Agent",
                        choices=AGENT_CHOICES,
                        value="auto (智能路由)",
                    )
                    mode_choice = gr.Dropdown(
                        label="输出模式",
                        choices=MODE_CHOICES,
                        value="standard (标准)",
                    )
                    difficulty_choice = gr.Dropdown(
                        label="习题难度 (仅 quiz_generator)",
                        choices=["default", "basic", "intermediate", "advanced", "all"],
                        value="default",
                    )
                    task_input = gr.Textbox(
                        label="任务描述",
                        placeholder="例如：为高中二年级设计一节「导数与切线」的教案...",
                        lines=3,
                    )
                    run_btn = gr.Button("🚀 执行", variant="primary", size="lg")

                with gr.Column(scale=2):
                    output_box = gr.Markdown(
                        value="👈 输入任务后点击执行",
                        elem_classes="output-box",
                    )
                    stats_box = gr.Textbox(
                        label="执行信息",
                        interactive=False,
                        elem_classes="stats-box",
                    )

            run_btn.click(
                fn=run_agent,
                inputs=[task_input, agent_choice, mode_choice, difficulty_choice],
                outputs=[output_box, stats_box],
            )

        # ── Pipeline 模式 ──
        with gr.TabItem("🔗 Pipeline 管线"):
            gr.Markdown("""
            ### 三 Agent 串行协作管线
            knowledge_mapper → lesson_planner → quiz_generator
            """)
            pipe_task1 = gr.Textbox(
                label="Step 1: 知识点拆解",
                placeholder="例如：拆解「高中物理·牛顿力学」的知识点",
            )
            pipe_task2 = gr.Textbox(
                label="Step 2: 教案生成",
                placeholder="例如：基于拆解结果生成牛顿第一定律教案",
            )
            pipe_task3 = gr.Textbox(
                label="Step 3: 习题生成",
                placeholder="例如：出5道牛顿力学配套练习题",
            )
            pipe_btn = gr.Button("🔗 执行管线", variant="primary")
            pipe_output = gr.Markdown(elem_classes="output-box")
            pipe_stats = gr.Textbox(label="执行信息", interactive=False)

            pipe_btn.click(
                fn=run_pipeline,
                inputs=[pipe_task1, pipe_task2, pipe_task3],
                outputs=[pipe_output, pipe_stats],
            )

        # ── 系统信息 ──
        with gr.TabItem("ℹ️ 系统信息"):
            status = orchestrator.get_status()
            gr.Markdown(f"""
            ## 系统状态

            | 项目 | 值 |
            |------|-----|
            | 模型 | `{status['model']}` |
            | 已注册 Agent | {', '.join(status['registered_agents'])} |
            | Agent 数量 | {status['agent_count']} |

            ## 关于 EduAgent

            EduAgent 是一个面向教学场景的轻量级多智能体框架，
            参加 [沐曦青年开源专项基金种子计划](https://mp.weixin.qq.com/s/tJ4KRSR-hQTeJN7zGsqLOw)。

            - 📦 GitHub: https://github.com/fengxaios/EduAgent
            - 📄 License: Apache 2.0
            - 🐍 Python: 3.10+
            """)


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True,
    )
