"""
EduAgent CLI — Command-line interface for quick agent invocation.
Usage: python -m eduagent [command] [options]
       eduagent [command] [options]  (after pip install)
"""

import argparse
import sys
from typing import Optional

from eduagent import __version__
from eduagent.core import Orchestrator


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eduagent",
        description="EduAgent — Lightweight multi-agent framework for teaching",
    )
    parser.add_argument(
        "--version", "-V", action="version", version=f"eduagent {__version__}"
    )
    parser.add_argument(
        "--model", "-m", default="qwen-plus",
        help="LLM model to use (default: qwen-plus)",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # lesson — generate lesson plan
    lp = sub.add_parser("lesson", help="Generate a lesson plan")
    lp.add_argument("topic", help="Teaching topic (e.g. '导数的几何意义')")
    lp.add_argument("--mode", choices=["brief", "standard", "detailed"], default="standard")

    # quiz — generate quiz questions
    qz = sub.add_parser("quiz", help="Generate quiz questions")
    qz.add_argument("topic", help="Knowledge point (e.g. '极限四则运算')")
    qz.add_argument("--difficulty", choices=["basic", "intermediate", "advanced", "all"], default="all")

    # map — knowledge mapping
    km = sub.add_parser("map", help="Decompose knowledge points")
    km.add_argument("topic", help="Subject/chapter (e.g. '不定积分')")
    km.add_argument("--mode", choices=["brief", "standard", "detailed"], default="standard")

    # pipeline — run multi-agent pipeline
    pl = sub.add_parser("pipeline", help="Run multi-agent pipeline")
    pl.add_argument("topic", help="Starting topic for the pipeline")
    pl.add_argument("--mode", choices=["brief", "standard", "detailed"], default="standard",
                    help="Output detail level for all agents")

    # diagnosis — learning diagnosis
    diag = sub.add_parser("diagnosis", help="Diagnose student learning gaps")
    diag.add_argument("topic", help="Knowledge area (e.g. '三角函数')")
    diag.add_argument("--student", "-s", default="", help="Student name")
    diag.add_argument("--mode", choices=["brief", "standard", "detailed"], default="standard")

    # profile — list agent profiles
    sub.add_parser("profiles", help="List all agent profiles with richness scores")

    # student — register student profile
    sp = sub.add_parser("student", help="Register or show student profile")
    sp.add_argument("name", help="Student name")
    sp.add_argument("--grade", "-g", default="", help="Grade level")
    sp.add_argument("--weak", "-w", default="", help="Weak points (comma separated)")

    # recommend — ZPD-based teaching recommendation
    rc = sub.add_parser("recommend", help="Get ZPD-based teaching recommendation")
    rc.add_argument("student", help="Student name")
    rc.add_argument("topic", help="Knowledge topic")

    # status
    sub.add_parser("status", help="Show orchestrator status")

    return parser


def run_lesson(orchestrator: Orchestrator, args: argparse.Namespace) -> str:
    from eduagent.agents import LessonPlannerAgent
    orchestrator.register(LessonPlannerAgent(mode=args.mode))
    result = orchestrator.route(f"设计一节关于{args.topic}的教案")
    return result["result"]


def run_quiz(orchestrator: Orchestrator, args: argparse.Namespace) -> str:
    from eduagent.agents import QuizGeneratorAgent
    orchestrator.register(QuizGeneratorAgent(difficulty=args.difficulty))
    result = orchestrator.route(f"出关于{args.topic}的练习题")
    return result["result"]


def run_map(orchestrator: Orchestrator, args: argparse.Namespace) -> str:
    from eduagent.agents import KnowledgeMapperAgent
    orchestrator.register(KnowledgeMapperAgent(mode=args.mode))
    result = orchestrator.route(f"拆解{args.topic}的知识点体系")
    return result["result"]


def run_pipeline(orchestrator: Orchestrator, args: argparse.Namespace) -> str:
    from eduagent.agents import (
        LessonPlannerAgent, QuizGeneratorAgent,
        KnowledgeMapperAgent, ReporterAgent,
        LearningDiagnosisAgent,
    )
    orchestrator.register_all([
        KnowledgeMapperAgent(mode=args.mode),
        LessonPlannerAgent(mode=args.mode),
        QuizGeneratorAgent(),
        LearningDiagnosisAgent(mode=args.mode),
        ReporterAgent(mode=args.mode),
    ])
    results = orchestrator.pipeline([
        {"agent": "knowledge_mapper", "task": f"拆解{args.topic}的知识点"},
        {"agent": "lesson_planner", "task": f"为{args.topic}生成教案"},
        {"agent": "quiz_generator", "task": f"为{args.topic}出5道练习题"},
        {"agent": "learning_diagnosis", "task": f"诊断{args.topic}学生答题情况"},
        {"agent": "reporter", "task": "生成完整教学报告"},
    ])
    # Aggregate pipeline output
    lines = [f"=== EduAgent Pipeline: {args.topic} ===", ""]
    for r in results:
        if "error" in r:
            lines.append(f"## {r['agent']}\nERROR: {r['error']}")
        else:
            lines.append(f"## {r['agent']}\n{r['result']}")
        lines.append("")
    return "\n".join(lines)


def run_diagnosis(orchestrator: Orchestrator, args: argparse.Namespace) -> str:
    from eduagent.agents import LearningDiagnosisAgent
    orchestrator.register(LearningDiagnosisAgent(
        mode=args.mode, student_name=args.student,
    ))
    task = f"诊断{args.topic}章节的学生答题情况"
    if args.student:
        task += f"，学生：{args.student}"
    result = orchestrator.route(task)
    return result["result"]


def main(argv: Optional[list] = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on error."""
    parser = get_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        orch = Orchestrator(model=args.model)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Set DASHSCOPE_API_KEY or pass --api-key", file=sys.stderr)
        return 1

    handlers = {
        "lesson": run_lesson,
        "quiz": run_quiz,
        "map": run_map,
        "pipeline": run_pipeline,
        "diagnosis": run_diagnosis,
        "profiles": None,  # handled inline
        "student": None,
        "recommend": None,
    }

    if args.command == "status":
        from eduagent.core import AgentProfile, StudentProfile
        print(f"EduAgent v{__version__} | Model: {orch.model}")
        print(f"  Agents: {len(orch.agents)} | Profiles: {len(orch.profiles)} | Students: {len(orch.student_pool)}")
        for name, agent in orch.agents.items():
            p_info = ""
            if name in orch.profiles:
                p_info = f" [richness={orch.profiles[name].profile_richness:.3f}]"
            print(f"  - {name}: {agent.__class__.__name__}{p_info}")
        return 0

    if args.command == "profiles":
        profiles = orch.list_profiles()
        if not profiles:
            print("没有注册任何 AgentProfile。")
        for p in profiles:
            print(f"\n📋 {p['name']} ({p['role']})")
            print(f"   描述: {p['description']}")
            print(f"   技能: {', '.join(p['skills'][:5])}")
            print(f"   丰富度: {p['profile_richness']:.3f}")
        return 0

    if args.command == "student":
        from eduagent.core import StudentProfile, ZPDLevel
        if args.name in orch.student_pool:
            s = orch.student_pool[args.name]
            print(f"👤 学生: {s.name}")
            print(f"   年级: {s.grade or '未知'}")
            print(f"   薄弱点: {', '.join(s.weak_points) or '无'}")
            print(f"   已掌握: {', '.join(s.known_points) or '无'}")
            print(f"   交互次数: {s.interaction_history}")
            return 0
        # 注册新学生
        sp = StudentProfile(
            name=args.name,
            grade=args.grade,
            weak_points=args.weak.split(",") if args.weak else [],
        )
        orch.register_student(sp)
        print(f"✅ 学生 {args.name} 已注册")
        return 0

    if args.command == "recommend":
        rec = orch.recommend_adaptation(args.student, args.topic)
        if "error" in rec:
            print(f"❌ {rec['error']}")
            return 1
        print(f"📊 ZPD 推荐策略")
        print(f"   学生: {rec['student']}")
        print(f"   主题: {rec['topic']}")
        print(f"   ZPD 层级: {rec['zpd_level']}")
        print(f"   建议操作: {rec['action']}")
        print(f"   推荐 Agent: {rec['agent']}")
        print(f"   难度: {rec['difficulty']}")
        return 0

    if args.command in handlers:
        try:
            result = handlers[args.command](orch, args)
            print(result)
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
