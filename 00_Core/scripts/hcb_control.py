import argparse
import importlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from arms.ai_engine import (
    generate_with_active_provider,
    load_engine_config,
    save_engine_config,
    set_active_provider,
)
from arms.concept_registry import list_concepts, upsert_concept
from arms.arm_memory_fabric import find_capsules, list_capsules, save_capsule
from arms.arm_tool_runner import build_tool_action, run_tool_action
from arms.event_bus import append_event, read_recent_events
from arms.planner_kernel import build_plan

ROOT = Path(__file__).resolve().parents[2]
TEMP_DIR = ROOT / "04_TEMP"
STORAGE_DIR = ROOT / "02_STORAGE"
ENGINES_DIR = ROOT / "00_Core" / "engines"
LOG_DIR = ROOT / "00_Core" / "logs"

SENTINEL_SRC = ROOT / "03_TRAINING" / "PRJ_02_SENTINEL" / "src"
NAPKIN_CHECKPOINT_DIR = Path(r"F:\PrimeiroProjetoTest\checkpoints")
AI_ENGINE_CONFIG = ROOT / "00_Core" / "config" / "ai_engine.json"
EVENT_LOG_PATH = ROOT / "00_Core" / "logs" / "event_bus.jsonl"
CONCEPT_REGISTRY_PATH = ROOT / "00_Core" / "contracts" / "concept_registry.json"


def ensure_import_path():
    sentinel_path = str(SENTINEL_SRC)
    if sentinel_path not in sys.path:
        sys.path.insert(0, sentinel_path)


def total_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*") if p.is_file())


def top_level_breakdown(path: Path) -> dict:
    result = {}
    if not path.exists():
        return result

    for child in path.iterdir():
        if child.is_dir():
            result[child.name] = total_files(child)
    return dict(sorted(result.items(), key=lambda item: item[0].lower()))


def build_status() -> dict:
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "root": str(ROOT),
        "temp_exists": TEMP_DIR.exists(),
        "storage_exists": STORAGE_DIR.exists(),
        "temp_file_count": total_files(TEMP_DIR),
        "storage_file_count": total_files(STORAGE_DIR),
        "storage_breakdown": top_level_breakdown(STORAGE_DIR),
        "brain_model_exists": (ENGINES_DIR / "brain_v1.pkl").exists(),
        "vectorizer_exists": (ENGINES_DIR / "vectorizer_v1.pkl").exists(),
        "bridge_dll_exists": (ENGINES_DIR / "hcb_bridge.dll").exists(),
        "native_sum_dll_exists": (ENGINES_DIR / "cpp_native" / "bin" / "hcb_core.dll").exists(),
    }


def summarize_napkin(checkpoint_dir: Path) -> dict:
    if not checkpoint_dir.exists():
        return {
            "checkpoint_dir": str(checkpoint_dir),
            "exists": False,
            "json_files": 0,
            "latest_timestamp": None,
            "key_modules": [],
        }

    files = sorted(checkpoint_dir.glob("*.json"))
    modules = {}
    latest = None
    latest_file = None

    for file in files:
        try:
            payload = json.loads(file.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue

        module = (
            payload.get("modulo")
            or payload.get("module")
            or payload.get("capsule_id")
            or "unknown"
        )
        modules[module] = modules.get(module, 0) + 1

        ts = payload.get("timestamp")
        if isinstance(ts, str):
            normalized = ts.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(normalized)
                if dt.tzinfo is not None:
                    dt_cmp = dt.astimezone().replace(tzinfo=None)
                else:
                    dt_cmp = dt

                if latest is None or dt_cmp > latest:
                    latest = dt_cmp
                    latest_file = file.name
            except ValueError:
                pass

    top_modules = sorted(modules.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "checkpoint_dir": str(checkpoint_dir),
        "exists": True,
        "json_files": len(files),
        "latest_timestamp": latest.isoformat() if latest else None,
        "latest_file": latest_file,
        "key_modules": [{"module": m, "count": c} for m, c in top_modules],
    }


def command_napkin(args):
    checkpoint_dir = Path(args.path)
    summary = summarize_napkin(checkpoint_dir)
    print("--- HCB NAPKIN SUMMARY ---")
    print(f"Path: {summary['checkpoint_dir']}")
    print(f"Exists: {summary['exists']}")
    print(f"JSON files: {summary['json_files']}")
    print(f"Latest timestamp: {summary['latest_timestamp']}")
    print(f"Latest file: {summary.get('latest_file')}")
    print("Key modules:")
    if not summary["key_modules"]:
        print("  (none)")
    else:
        for item in summary["key_modules"]:
            print(f"  - {item['module']}: {item['count']}")

    if args.write_report:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        report_path = LOG_DIR / f"hcb_napkin_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Report written to: {report_path}")


def command_arm_tool(args):
    control_script = Path(__file__).resolve()
    action = build_tool_action(args.intent, control_script)
    result = run_tool_action(action, dry_run=args.dry_run)

    print("--- HCB ARM TOOL RUNNER ---")
    print(f"Intent: {result['intent']}")
    print(f"Resolved args: {result['resolved_args']}")
    print(f"Command: {result['command_pretty']}")
    print(f"Dry run: {result['dry_run']}")
    print(f"Result: {'OK' if result['ok'] else 'FAIL'} (rc={result['returncode']})")

    if result["stdout"]:
        print("\nstdout:")
        print(result["stdout"])
    if result["stderr"]:
        print("\nstderr:")
        print(result["stderr"])


def command_arm_memory_save(args):
    path = save_capsule(
        root=ROOT,
        modulo=args.modulo,
        atividade=args.atividade,
        comentarios=args.comentarios,
        ia_origem=args.source,
    )
    print(f"Capsule saved: {path}")


def _print_capsule_rows(rows: list[dict]):
    if not rows:
        print("(none)")
        return
    for row in rows:
        print(
            f"- {row.get('timestamp')} | {row.get('modulo')} | {row.get('atividade')} | {row.get('path')}"
        )


def command_arm_memory_list(args):
    rows = list_capsules(ROOT, limit=args.limit)
    print("--- HCB ARM MEMORY LIST ---")
    _print_capsule_rows(rows)


def command_arm_memory_find(args):
    rows = find_capsules(ROOT, query=args.query, limit=args.limit)
    print(f"--- HCB ARM MEMORY FIND: '{args.query}' ---")
    _print_capsule_rows(rows)


def _log_ai_response(result: dict) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"hcb_ai_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out = LOG_DIR / file_name
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def command_ai_status(_args):
    cfg = load_engine_config(AI_ENGINE_CONFIG)
    if not AI_ENGINE_CONFIG.exists():
        save_engine_config(AI_ENGINE_CONFIG, cfg)
    active = cfg.get("active_provider")
    p = (cfg.get("providers") or {}).get(active, {})
    print("--- HCB AI ENGINE STATUS ---")
    print(f"Config: {AI_ENGINE_CONFIG}")
    print(f"Active provider: {active}")
    print(f"Model: {p.get('model')}")
    print(f"Enabled: {p.get('enabled')}")
    print(f"API key env: {p.get('api_key_env')}")


def command_ai_set(args):
    cfg = set_active_provider(AI_ENGINE_CONFIG, provider=args.provider, model=args.model)
    active = cfg["active_provider"]
    model = cfg["providers"][active].get("model")
    print("--- HCB AI ENGINE UPDATED ---")
    print(f"Active provider: {active}")
    print(f"Model: {model}")
    print(f"Config saved: {AI_ENGINE_CONFIG}")


def command_ai_test(args):
    result = generate_with_active_provider(AI_ENGINE_CONFIG, args.prompt)
    print("--- HCB AI ENGINE TEST ---")
    print(f"Provider: {result.get('provider')}")
    print(f"Model: {result.get('model')}")
    print(f"Timestamp: {result.get('timestamp')}")
    print("\nResponse:")
    print(result.get("text", ""))

    if args.write_report:
        report_path = _log_ai_response(result)
        print(f"\nReport written to: {report_path}")


def command_event_emit(args):
    payload = {"note": args.note} if args.note else {}
    event = append_event(EVENT_LOG_PATH, args.event_type, payload)
    print("--- HCB EVENT EMIT ---")
    print(json.dumps(event, indent=2, ensure_ascii=False))


def command_event_tail(args):
    rows = read_recent_events(EVENT_LOG_PATH, limit=args.limit)
    print(f"--- HCB EVENT TAIL (last {args.limit}) ---")
    if not rows:
        print("(none)")
        return
    for row in rows:
        print(f"- {row.get('timestamp')} | {row.get('event_type')} | {row.get('event_id')}")


def command_concept_add(args):
    concept = upsert_concept(
        CONCEPT_REGISTRY_PATH,
        name=args.name,
        hypothesis=args.hypothesis,
        status=args.status,
        evidence=args.evidence,
    )
    append_event(
        EVENT_LOG_PATH,
        "concept_upserted",
        {"name": concept.get("name"), "status": concept.get("status")},
    )
    print("--- HCB CONCEPT UPSERT ---")
    print(json.dumps(concept, indent=2, ensure_ascii=False))


def command_concept_list(_args):
    concepts = list_concepts(CONCEPT_REGISTRY_PATH)
    print("--- HCB CONCEPTS ---")
    if not concepts:
        print("(none)")
        return
    for c in concepts:
        print(f"- {c.get('name')} | {c.get('status')} | updated: {c.get('updated_at')}")


def command_kernel_plan(args):
    plan = build_plan(args.goal)
    append_event(EVENT_LOG_PATH, "plan_created", {"goal": plan["goal"], "steps": len(plan["steps"])})
    print("--- HCB KERNEL PLAN ---")
    print(json.dumps(plan, indent=2, ensure_ascii=False))


def command_kernel_execute(args):
    plan = build_plan(args.goal)
    append_event(EVENT_LOG_PATH, "plan_execution_started", {"goal": plan["goal"], "steps": len(plan["steps"])})
    print("--- HCB KERNEL EXECUTE ---")
    print(f"Goal: {plan['goal']}")
    all_ok = True
    control_script = Path(__file__).resolve()

    for i, step in enumerate(plan["steps"], start=1):
        action = {
            "intent": step["step"],
            "resolved_args": step["command_args"],
            "command": [sys.executable, str(control_script), *step["command_args"]],
        }
        result = run_tool_action(action, dry_run=args.dry_run)
        step_ok = result.get("ok", False)
        all_ok = all_ok and step_ok
        print(f"{i}. {step['step']} -> {'OK' if step_ok else 'FAIL'}")
        append_event(
            EVENT_LOG_PATH,
            "plan_step_executed",
            {
                "goal": plan["goal"],
                "step_index": i,
                "step": step["step"],
                "ok": step_ok,
                "returncode": result.get("returncode"),
            },
        )

    append_event(
        EVENT_LOG_PATH,
        "plan_execution_finished",
        {"goal": plan["goal"], "ok": all_ok, "dry_run": args.dry_run},
    )
    print(f"Final result: {'OK' if all_ok else 'FAIL'}")


def print_status(status: dict):
    print("--- HCB STATUS ---")
    print(f"Timestamp: {status['timestamp']}")
    print(f"Root: {status['root']}")
    print(f"Temp files: {status['temp_file_count']}")
    print(f"Storage files: {status['storage_file_count']}")
    print(
        "Models: brain={brain} vectorizer={vec}".format(
            brain=status["brain_model_exists"],
            vec=status["vectorizer_exists"],
        )
    )
    print(
        "Engines: bridge_dll={bridge} native_sum_dll={native}".format(
            bridge=status["bridge_dll_exists"],
            native=status["native_sum_dll_exists"],
        )
    )
    print("Storage breakdown:")
    if not status["storage_breakdown"]:
        print("  (empty)")
    else:
        for folder, count in status["storage_breakdown"].items():
            print(f"  - {folder}: {count}")


def run_triage_cycle(mode: str):
    ensure_import_path()
    if mode == "core":
        module = importlib.import_module("sentinel_core")
        module.sort_files()
    else:
        module = importlib.import_module("sentinel_smart")
        module.smart_sort_v3()


def command_status(args):
    status = build_status()
    print_status(status)
    if args.json:
        print(json.dumps(status, indent=2, ensure_ascii=False))


def command_train(_args):
    ensure_import_path()
    module = importlib.import_module("brain_trainer")
    module.train_brain()


def command_triage(args):
    print("--- HCB TRIAGE ---")
    print(f"Mode: {args.mode} | Interval: {args.interval}s | Watch: {args.watch}")
    try:
        if not args.watch:
            run_triage_cycle(args.mode)
            return

        while True:
            run_triage_cycle(args.mode)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nTriage stopped by user.")


def write_report(report: dict) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    report_name = f"hcb_evolve_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = LOG_DIR / report_name
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report_path


def command_evolve(args):
    report = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": args.mode,
        "cycles": args.cycles,
        "trained": False,
        "status_before": build_status(),
        "status_after": None,
    }

    if args.train_first:
        command_train(args)
        report["trained"] = True

    print(f"Running evolve pipeline with {args.cycles} cycle(s)...")
    for _ in range(args.cycles):
        run_triage_cycle(args.mode)
        if args.interval > 0:
            time.sleep(args.interval)

    report["status_after"] = build_status()
    report_path = write_report(report)
    print(f"Evolve report written to: {report_path}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="HCB Control Center - operational CLI for Sentinel and Core"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="show system status")
    status_parser.add_argument("--json", action="store_true", help="print raw status json")
    status_parser.set_defaults(func=command_status)

    train_parser = subparsers.add_parser("train", help="train and persist Sentinel brain")
    train_parser.set_defaults(func=command_train)

    triage_parser = subparsers.add_parser("triage", help="run file triage (core or smart)")
    triage_parser.add_argument("--mode", choices=["core", "smart"], default="smart")
    triage_parser.add_argument("--interval", type=float, default=2.0)
    triage_parser.add_argument("--watch", action="store_true", help="run continuously")
    triage_parser.set_defaults(func=command_triage)

    evolve_parser = subparsers.add_parser("evolve", help="run a complete operational cycle")
    evolve_parser.add_argument("--mode", choices=["core", "smart"], default="smart")
    evolve_parser.add_argument("--cycles", type=int, default=1)
    evolve_parser.add_argument("--interval", type=float, default=0.0)
    evolve_parser.add_argument("--train-first", action="store_true")
    evolve_parser.set_defaults(func=command_evolve)

    napkin_parser = subparsers.add_parser(
        "napkin",
        help="summarize external checkpoint capsules (guardanapo do cientista)",
    )
    napkin_parser.add_argument("--path", default=str(NAPKIN_CHECKPOINT_DIR))
    napkin_parser.add_argument("--write-report", action="store_true")
    napkin_parser.set_defaults(func=command_napkin)

    arm_tool_parser = subparsers.add_parser(
        "arm-tool",
        help="run first operational arm: map an intent to a control action",
    )
    arm_tool_parser.add_argument("intent")
    arm_tool_parser.add_argument("--dry-run", action="store_true")
    arm_tool_parser.set_defaults(func=command_arm_tool)

    arm_memory_parser = subparsers.add_parser(
        "arm-memory",
        help="memory fabric arm: save/list/find capsules for HCB Studio",
    )
    arm_memory_sub = arm_memory_parser.add_subparsers(dest="arm_memory_command", required=True)

    arm_memory_save = arm_memory_sub.add_parser("save", help="save a capsule")
    arm_memory_save.add_argument("--modulo", required=True)
    arm_memory_save.add_argument("--atividade", required=True)
    arm_memory_save.add_argument("--comentarios", default="")
    arm_memory_save.add_argument("--source", default="HCB-Control")
    arm_memory_save.set_defaults(func=command_arm_memory_save)

    arm_memory_list = arm_memory_sub.add_parser("list", help="list saved capsules")
    arm_memory_list.add_argument("--limit", type=int, default=20)
    arm_memory_list.set_defaults(func=command_arm_memory_list)

    arm_memory_find = arm_memory_sub.add_parser("find", help="search capsules by query")
    arm_memory_find.add_argument("--query", required=True)
    arm_memory_find.add_argument("--limit", type=int, default=20)
    arm_memory_find.set_defaults(func=command_arm_memory_find)

    ai_parser = subparsers.add_parser(
        "ai",
        help="single active AI engine (Gemini now, extensible later)",
    )
    ai_sub = ai_parser.add_subparsers(dest="ai_command", required=True)

    ai_status = ai_sub.add_parser("status", help="show active AI engine configuration")
    ai_status.set_defaults(func=command_ai_status)

    ai_set = ai_sub.add_parser("set", help="set active AI provider/model")
    ai_set.add_argument("--provider", choices=["gemini"], default="gemini")
    ai_set.add_argument("--model", default=None)
    ai_set.set_defaults(func=command_ai_set)

    ai_test = ai_sub.add_parser("test", help="run a prompt on the active AI engine")
    ai_test.add_argument("--prompt", required=True)
    ai_test.add_argument("--write-report", action="store_true")
    ai_test.set_defaults(func=command_ai_test)

    event_parser = subparsers.add_parser("event", help="event bus operations")
    event_sub = event_parser.add_subparsers(dest="event_command", required=True)

    event_emit = event_sub.add_parser("emit", help="append an event to event bus")
    event_emit.add_argument("--event-type", required=True)
    event_emit.add_argument("--note", default="")
    event_emit.set_defaults(func=command_event_emit)

    event_tail = event_sub.add_parser("tail", help="read recent events")
    event_tail.add_argument("--limit", type=int, default=20)
    event_tail.set_defaults(func=command_event_tail)

    concept_parser = subparsers.add_parser("concept", help="concept registry operations")
    concept_sub = concept_parser.add_subparsers(dest="concept_command", required=True)

    concept_add = concept_sub.add_parser("add", help="add or update a concept")
    concept_add.add_argument("--name", required=True)
    concept_add.add_argument("--hypothesis", required=True)
    concept_add.add_argument("--status", default="draft")
    concept_add.add_argument("--evidence", default="")
    concept_add.set_defaults(func=command_concept_add)

    concept_list = concept_sub.add_parser("list", help="list registered concepts")
    concept_list.set_defaults(func=command_concept_list)

    kernel_parser = subparsers.add_parser("kernel", help="planner kernel operations")
    kernel_sub = kernel_parser.add_subparsers(dest="kernel_command", required=True)

    kernel_plan = kernel_sub.add_parser("plan", help="build a plan from a goal")
    kernel_plan.add_argument("--goal", required=True)
    kernel_plan.set_defaults(func=command_kernel_plan)

    kernel_exec = kernel_sub.add_parser("execute", help="execute planned steps from a goal")
    kernel_exec.add_argument("--goal", required=True)
    kernel_exec.add_argument("--dry-run", action="store_true")
    kernel_exec.set_defaults(func=command_kernel_execute)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
