import argparse
import importlib
import json
import subprocess
import sys
import tempfile
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
from arms.hcb_identity import SCI_ONBOARDING_QUESTIONS, create_hcb_state, create_sci_profile, run_sci_onboarding_wizard
from arms.arm_memory_fabric import find_capsules, list_capsules, save_capsule
from arms.arm_tool_runner import build_tool_action, run_tool_action
from arms.event_bus import append_event, read_recent_events
from arms.planner_kernel import build_plan
from arms.arm_09_prompt_writer import generate_production_prompts
from arms.arm_10_block_organizer import (
    create_project,
    ingest_prompt_blocks,
    list_projects,
    refresh_dependencies,
    scan_generated_assets,
    update_block,
)

ROOT = Path(__file__).resolve().parents[2]
TEMP_DIR = ROOT / "04_TEMP"
STORAGE_DIR = ROOT / "02_STORAGE"
ENGINES_DIR = ROOT / "00_Core" / "engines"
LOG_DIR = ROOT / "00_Core" / "logs"
RUST_COORDINATOR_DIR = ROOT / "00_Core" / "runtime" / "rust_coordinator"
RUST_COORDINATOR_EXE = RUST_COORDINATOR_DIR / "target" / "debug" / "rust_coordinator.exe"

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


def command_identity_init(args):
    path = create_sci_profile(
        root=ROOT,
        user_id=args.user_id,
        display_name=args.display_name,
        primary_language=args.primary_language,
        timezone_name=args.timezone_name,
        role_profile=args.role_profile,
        technical_level=args.technical_level,
        preferred_tone=args.preferred_tone,
        response_depth=args.response_depth,
        step_by_step=args.step_by_step,
        correction_style=args.correction_style,
        needs_adaptation=args.needs_adaptation,
        visual_support=args.visual_support,
        motor_support=args.motor_support,
        fatigue_support=args.fatigue_support,
        accessibility_notes=args.accessibility_notes,
    )
    print(f"SCI profile created: {path}")


def command_identity_questions(_args):
    print("--- HCB SCI ONBOARDING QUESTIONS ---")
    for row in SCI_ONBOARDING_QUESTIONS:
        print(f"- {row}")


def command_identity_wizard(args):
    path = run_sci_onboarding_wizard(ROOT, user_id=args.user_id)
    print(f"SCI profile created via wizard: {path}")


def command_state_init(args):
    path = create_hcb_state(
        root=ROOT,
        user_id=args.user_id,
        mode=args.mode,
        energy=args.energy,
        focus=args.focus,
        urgency=args.urgency,
        cognitive_load=args.cognitive_load,
        response_preference=args.response_preference,
        active_project=args.active_project,
        notes=args.notes,
        fatigue_now=args.fatigue_now,
        pain_now=args.pain_now,
        visual_overload=args.visual_overload,
        needs_pause=args.needs_pause,
    )
    print(f"HCB state created: {path}")


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
    payload = {
        "config": str(AI_ENGINE_CONFIG),
        "active_provider": active,
        "model": p.get("model"),
        "enabled": p.get("enabled"),
        "api_key_env": p.get("api_key_env"),
    }
    if getattr(_args, "json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    print("--- HCB AI ENGINE STATUS ---")
    print(f"Config: {payload['config']}")
    print(f"Active provider: {payload['active_provider']}")
    print(f"Model: {payload['model']}")
    print(f"Enabled: {payload['enabled']}")
    print(f"API key env: {payload['api_key_env']}")


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
    if getattr(args, "json", False):
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
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


def command_concept_list(args):
    concepts = list_concepts(CONCEPT_REGISTRY_PATH)
    if getattr(args, "json", False):
        print(json.dumps(concepts, indent=2, ensure_ascii=False))
        return
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
        
        if not step_ok:
            print(f"❌ CRITICAL FAILURE at step {i}: {step['step']}. Halting and rolling back.")
            _create_system_checkpoint(note=f"Rollback state after failure during: {step['step']}", retention_class="ephemeral")
            break

    append_event(
        EVENT_LOG_PATH,
        "plan_execution_finished",
        {"goal": plan["goal"], "ok": all_ok, "dry_run": args.dry_run},
    )
    print(f"Final result: {'OK' if all_ok else 'FAIL'}")
    
    if all_ok:
        print("✅ Plan executed successfully. Generating final state checkpoint.")
        _create_system_checkpoint(note=f"Successful execution of goal: {plan['goal']}", retention_class="ephemeral")


def _build_command_record(goal: str, source: str = "cli_planner") -> dict:
    import uuid
    from datetime import datetime, timezone

    plan = build_plan(goal)
    return {
        "command_id": str(uuid.uuid4()),
        "intent": goal,
        "action": "execute_plan",
        "payload": {
            "steps": plan.get("steps", [])
        },
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source
        }
    }


def _build_cli_proxy_command(action: str, command_args: list[str], source: str) -> dict:
    import uuid
    from datetime import datetime, timezone

    control_script = Path(__file__).resolve()
    return {
        "command_id": str(uuid.uuid4()),
        "intent": f"rust_proxy::{action}",
        "action": "run_cli_command",
        "payload": {
            "program": sys.executable,
            "args": [str(control_script), *command_args],
            "parse_json_stdout": True,
        },
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
        },
    }


def _run_rust_coordinator(command_record: dict) -> dict:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    command_path = TEMP_DIR / f"coordinator_command_{command_record['command_id']}.json"
    result_path = TEMP_DIR / f"coordinator_result_{command_record['command_id']}.json"
    command_path.write_text(json.dumps(command_record, indent=2, ensure_ascii=False), encoding="utf-8")

    if RUST_COORDINATOR_EXE.exists():
        cmd = [
            str(RUST_COORDINATOR_EXE),
            "process",
            "--command-file",
            str(command_path),
            "--result-file",
            str(result_path),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    else:
        cmd = [
            "cargo",
            "run",
            "--quiet",
            "--",
            "process",
            "--command-file",
            str(command_path),
            "--result-file",
            str(result_path),
        ]
        completed = subprocess.run(cmd, cwd=RUST_COORDINATOR_DIR, capture_output=True, text=True, check=False)

    if completed.returncode != 0:
        raise RuntimeError(
            "Rust coordinator failed: "
            + (completed.stderr.strip() or completed.stdout.strip() or f"rc={completed.returncode}")
        )

    if not result_path.exists():
        raise FileNotFoundError(f"Rust coordinator did not write result file: {result_path}")

    return json.loads(result_path.read_text(encoding="utf-8"))


def _create_system_checkpoint(note: str = "", retention_class: str = "ephemeral") -> dict:
    import uuid
    from datetime import datetime, timezone
    
    state_snap = build_status()
    checkpoint_record = {
        "checkpoint_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retention_class": retention_class,
        "state": state_snap,
        "context": {
            "note": note
        },
        "next_actions": []
    }
    out_file = STORAGE_DIR / "checkpoints" / f"ckpt_{checkpoint_record['checkpoint_id']}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(checkpoint_record, indent=2, ensure_ascii=False), encoding="utf-8")
    
    _cleanup_ephemeral_checkpoints()
    
    return checkpoint_record


def _cleanup_ephemeral_checkpoints(limit: int = 15):
    """Keeps only the latest N ephemeral checkpoints, ignores immortals."""
    target_dir = STORAGE_DIR / "checkpoints"
    if not target_dir.exists():
        return
        
    ephemerals = []
    
    for file in target_dir.glob("ckpt_*.json"):
        try:
            payload = json.loads(file.read_text(encoding="utf-8", errors="ignore"))
            if payload.get("retention_class") == "ephemeral":
                ephemerals.append((file, file.stat().st_mtime))
        except Exception:
            pass
            
    # Sort backwards by time (newest first)
    ephemerals.sort(key=lambda x: x[1], reverse=True)
    
    # Delete everything past the limit
    for file, _ in ephemerals[limit:]:
        try:
            file.unlink(missing_ok=True)
            print(f"Rotated out old ephemeral checkpoint: {file.name}")
        except Exception as e:
            print(f"Failed to delete old checkpoint {file}: {e}")

def command_planner(args):
    command_record = _build_command_record(args.goal, source="cli_planner")
    
    print(json.dumps(command_record, indent=2))
    
    # Optional: save to file
    out_file = TEMP_DIR / f"plan_{command_record['command_id']}.json"
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(command_record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Schema-compliant plan saved to {out_file}", file=sys.stderr)

    if args.dispatch == "rust":
        result = _run_rust_coordinator(command_record)
        append_event(
            EVENT_LOG_PATH,
            "rust_coordinator_dispatched",
            {
                "command_id": command_record["command_id"],
                "status": result.get("status"),
            },
        )
        print("\n--- HCB RUST COORDINATOR RESULT ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))


def command_coordinator_demo(_args):
    if RUST_COORDINATOR_EXE.exists():
        cmd = [str(RUST_COORDINATOR_EXE), "demo"]
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    else:
        cmd = ["cargo", "run", "--quiet", "--", "demo"]
        completed = subprocess.run(cmd, cwd=RUST_COORDINATOR_DIR, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Rust coordinator demo failed.")
    print(completed.stdout.strip())


def command_coordinator_run_safe(args):
    if args.action == "status":
        command_record = _build_cli_proxy_command(
            action="status",
            command_args=["status", "--json-only"],
            source="coordinator_safe_status",
        )
    elif args.action == "ai-status":
        command_record = _build_cli_proxy_command(
            action="ai_status",
            command_args=["ai", "status", "--json"],
            source="coordinator_safe_ai_status",
        )
    elif args.action == "event-tail":
        command_record = _build_cli_proxy_command(
            action="event_tail",
            command_args=["event", "tail", "--limit", str(args.limit), "--json"],
            source="coordinator_safe_event_tail",
        )
    elif args.action == "concept-list":
        command_record = _build_cli_proxy_command(
            action="concept_list",
            command_args=["concept", "list", "--json"],
            source="coordinator_safe_concept_list",
        )
    else:
        command_record = _build_cli_proxy_command(
            action="organizer_list_projects",
            command_args=["organizer", "list-projects", "--json"],
            source="coordinator_safe_organizer_list",
        )

    result = _run_rust_coordinator(command_record)
    append_event(
        EVENT_LOG_PATH,
        "rust_coordinator_safe_action",
        {
            "command_id": command_record["command_id"],
            "safe_action": args.action,
            "status": result.get("status"),
        },
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))


def command_checkpoint(args):
    if args.action != "end-of-block":
        print("Only end-of-block is supported currently.")
        return

    checkpoint_record = _create_system_checkpoint(note=args.note, retention_class="immortal")
    print(json.dumps(checkpoint_record, indent=2))
    print(f"Immortal Checkpoint saved.", file=sys.stderr)


def command_prompt_generate(args):
    payload = generate_production_prompts(
        AI_ENGINE_CONFIG,
        idea=args.idea,
        target_tool=args.target,
        language=args.language
    )

    blocks_dir = STORAGE_DIR / "blocks" / "prompt_queue"
    blocks_dir.mkdir(parents=True, exist_ok=True)
    out_file = blocks_dir / f"{payload['block_id']}.json"
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    append_event(
        EVENT_LOG_PATH,
        "prompt_block_generated",
        {
            "block_id": payload["block_id"],
            "target_tool": payload["ferramenta_destino"],
            "asset_type": payload["tipo_de_ativo"],
            "validation_issues": payload.get("validation_issues", []),
        },
    )

    print("--- HCB ARM 09: UNIVERSAL PROMPT WRITER ---")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nPrompt artifact saved to: {out_file}", file=sys.stderr)


def command_organizer_create_project(args):
    project = create_project(
        STORAGE_DIR,
        project_id=args.project_id,
        project_drawer=args.project_drawer,
        name=args.name,
        goal=args.goal,
    )
    append_event(
        EVENT_LOG_PATH,
        "arm10_project_created",
        {
            "project_id": project["project_id"],
            "project_drawer": project["project_drawer"],
        },
    )
    print("--- HCB ARM 10: CREATE PROJECT ---")
    print(json.dumps(project, indent=2, ensure_ascii=False))


def command_organizer_ingest(args):
    result = ingest_prompt_blocks(
        STORAGE_DIR,
        project_drawer=args.project_drawer,
        block_id=args.block_id,
    )
    append_event(
        EVENT_LOG_PATH,
        "arm10_blocks_ingested",
        {
            "project_drawer": result["project_drawer"],
            "ingested_count": result["ingested_count"],
        },
    )
    print("--- HCB ARM 10: INGEST BLOCKS ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def command_organizer_update_block(args):
    result = update_block(
        STORAGE_DIR,
        project_drawer=args.project_drawer,
        block_id=args.block_id,
        status=args.status,
        file_reference=args.file_reference,
        track=args.track,
        in_point_ms=args.in_point_ms,
        out_point_ms=args.out_point_ms,
        source_ai=args.source_ai,
        notes=args.notes,
    )
    append_event(
        EVENT_LOG_PATH,
        "arm10_block_updated",
        {
            "project_drawer": args.project_drawer,
            "block_id": args.block_id,
            "status": result.get("status"),
        },
    )
    print("--- HCB ARM 10: UPDATE BLOCK ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def command_organizer_list_projects(args):
    rows = list_projects(STORAGE_DIR)
    if getattr(args, "json", False):
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    print("--- HCB ARM 10: PROJECTS ---")
    if not rows:
        print("(none)")
        return
    for row in rows:
        print(
            f"- {row.get('project_drawer')} | {row.get('nome')} | {row.get('estado_global')} | {row.get('timeline_file')}"
        )


def command_organizer_scan_assets(args):
    result = scan_generated_assets(STORAGE_DIR, project_drawer=args.project_drawer)
    append_event(
        EVENT_LOG_PATH,
        "arm10_assets_scanned",
        {
            "project_drawer": result["project_drawer"],
            "matched_count": result["matched_count"],
        },
    )
    print("--- HCB ARM 10: SCAN ASSETS ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def command_organizer_refresh_dependencies(args):
    result = refresh_dependencies(STORAGE_DIR, project_drawer=args.project_drawer)
    append_event(
        EVENT_LOG_PATH,
        "arm10_dependencies_refreshed",
        {
            "project_drawer": result["project_drawer"],
            "block_count": len(result["blocks"]),
        },
    )
    print("--- HCB ARM 10: REFRESH DEPENDENCIES ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))


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
    if getattr(args, "json_only", False):
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return
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
    status_parser.add_argument("--json-only", action="store_true", help="print only raw status json")
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

    identity_parser = subparsers.add_parser("identity", help="SCI user identity bootstrap")
    identity_sub = identity_parser.add_subparsers(dest="identity_command", required=True)

    identity_init = identity_sub.add_parser("init", help="create a stable SCI user profile")
    identity_init.add_argument("--user-id", required=True)
    identity_init.add_argument("--display-name", required=True)
    identity_init.add_argument("--primary-language", default="pt-BR")
    identity_init.add_argument("--timezone-name", default="Europe/London")
    identity_init.add_argument(
        "--role-profile",
        choices=["general", "creator", "student", "teacher", "researcher", "business", "developer"],
        default="general",
    )
    identity_init.add_argument(
        "--technical-level",
        choices=["beginner", "intermediate", "advanced"],
        default="intermediate",
    )
    identity_init.add_argument("--preferred-tone", choices=["direct", "balanced", "gentle"], default="balanced")
    identity_init.add_argument("--response-depth", choices=["short", "balanced", "deep"], default="balanced")
    identity_init.add_argument("--step-by-step", action="store_true")
    identity_init.add_argument("--correction-style", choices=["explicit", "gentle", "mixed"], default="mixed")
    identity_init.add_argument("--needs-adaptation", action="store_true")
    identity_init.add_argument("--visual-support", action="store_true")
    identity_init.add_argument("--motor-support", action="store_true")
    identity_init.add_argument("--fatigue-support", action="store_true")
    identity_init.add_argument("--accessibility-notes", default="")
    identity_init.set_defaults(func=command_identity_init)

    identity_questions = identity_sub.add_parser("questions", help="list the objective SCI onboarding questions")
    identity_questions.set_defaults(func=command_identity_questions)

    identity_wizard = identity_sub.add_parser("wizard", help="run the SCI onboarding wizard in the terminal")
    identity_wizard.add_argument("--user-id", required=True)
    identity_wizard.set_defaults(func=command_identity_wizard)

    state_parser = subparsers.add_parser("state", help="HCB dynamic state bootstrap")
    state_sub = state_parser.add_subparsers(dest="state_command", required=True)

    state_init = state_sub.add_parser("init", help="create the dynamic HCB state for a user")
    state_init.add_argument("--user-id", required=True)
    state_init.add_argument(
        "--mode",
        choices=["study", "work", "creation", "research", "review", "support"],
        default="work",
    )
    state_init.add_argument("--energy", choices=["low", "medium", "high"], default="medium")
    state_init.add_argument("--focus", choices=["scattered", "normal", "deep"], default="normal")
    state_init.add_argument("--urgency", choices=["low", "medium", "high"], default="medium")
    state_init.add_argument("--cognitive-load", choices=["light", "moderate", "heavy"], default="moderate")
    state_init.add_argument(
        "--response-preference",
        choices=["summary", "balanced", "detailed"],
        default="balanced",
    )
    state_init.add_argument("--active-project", default="")
    state_init.add_argument("--notes", default="")
    state_init.add_argument("--fatigue-now", action="store_true")
    state_init.add_argument("--pain-now", action="store_true")
    state_init.add_argument("--visual-overload", action="store_true")
    state_init.add_argument("--needs-pause", action="store_true")
    state_init.set_defaults(func=command_state_init)

    ai_parser = subparsers.add_parser(
        "ai",
        help="single active AI engine (Gemini now, extensible later)",
    )
    ai_sub = ai_parser.add_subparsers(dest="ai_command", required=True)

    ai_status = ai_sub.add_parser("status", help="show active AI engine configuration")
    ai_status.add_argument("--json", action="store_true", help="print only raw ai status json")
    ai_status.set_defaults(func=command_ai_status)

    ai_set = ai_sub.add_parser("set", help="set active AI provider/model")
    ai_set.add_argument("--provider", choices=["gemini", "ollama"], default="gemini")
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
    event_tail.add_argument("--json", action="store_true", help="print only raw events json")
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
    concept_list.add_argument("--json", action="store_true", help="print only raw concepts json")
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

    planner_parser = subparsers.add_parser("planner", help="generate schema-compliant plan record")
    planner_parser.add_argument("--goal", required=True)
    planner_parser.add_argument("--dispatch", choices=["none", "rust"], default="none")
    planner_parser.set_defaults(func=command_planner)

    coordinator_parser = subparsers.add_parser("coordinator", help="Rust coordinator bridge operations")
    coordinator_sub = coordinator_parser.add_subparsers(dest="coordinator_command", required=True)

    coordinator_demo = coordinator_sub.add_parser("demo", help="run Rust coordinator demo loop")
    coordinator_demo.set_defaults(func=command_coordinator_demo)

    coordinator_safe = coordinator_sub.add_parser(
        "run-safe",
        help="execute a safe Studio command through the Rust coordinator",
    )
    coordinator_safe.add_argument(
        "--action",
        choices=["status", "ai-status", "event-tail", "concept-list", "organizer-list-projects"],
        required=True,
    )
    coordinator_safe.add_argument("--limit", type=int, default=10, help="used by event-tail")
    coordinator_safe.set_defaults(func=command_coordinator_run_safe)

    checkpoint_parser = subparsers.add_parser("checkpoint", help="persist continuity capsule at each stop")
    checkpoint_parser.add_argument("action", choices=["end-of-block"], help="the checkpoint action to perform")
    checkpoint_parser.add_argument("--note", default="", help="optional context note")
    checkpoint_parser.set_defaults(func=command_checkpoint)
    
    prompt_parser = subparsers.add_parser("prompt", help="Arm 09 Universal Prompt Writer operations")
    prompt_sub = prompt_parser.add_subparsers(dest="prompt_command", required=True)
    
    prompt_gen = prompt_sub.add_parser("generate", help="generate production-ready prompts from a raw idea")
    prompt_gen.add_argument("idea", help="the raw creative concept")
    prompt_gen.add_argument("--target", required=True, help="the target AI tool (midjourney, elevenlabs, etc)")
    prompt_gen.add_argument("--language", default="en", help="the language of the final generated prompt")
    prompt_gen.set_defaults(func=command_prompt_generate)

    organizer_parser = subparsers.add_parser("organizer", help="Arm 10 Production Block Organizer operations")
    organizer_sub = organizer_parser.add_subparsers(dest="organizer_command", required=True)

    organizer_create = organizer_sub.add_parser("create-project", help="create a dedicated project drawer")
    organizer_create.add_argument("--project-id", required=True)
    organizer_create.add_argument("--project-drawer", required=True)
    organizer_create.add_argument("--name", required=True)
    organizer_create.add_argument("--goal", required=True)
    organizer_create.set_defaults(func=command_organizer_create_project)

    organizer_ingest = organizer_sub.add_parser("ingest", help="ingest Arm 09 prompt blocks into a project")
    organizer_ingest.add_argument("--project-drawer", required=True)
    organizer_ingest.add_argument("--block-id", default=None)
    organizer_ingest.set_defaults(func=command_organizer_ingest)

    organizer_update = organizer_sub.add_parser("update-block", help="update a block inside a project timeline")
    organizer_update.add_argument("--project-drawer", required=True)
    organizer_update.add_argument("--block-id", required=True)
    organizer_update.add_argument("--status", default=None)
    organizer_update.add_argument("--file-reference", default=None)
    organizer_update.add_argument("--track", default=None)
    organizer_update.add_argument("--in-point-ms", type=int, default=None)
    organizer_update.add_argument("--out-point-ms", type=int, default=None)
    organizer_update.add_argument("--source-ai", default=None)
    organizer_update.add_argument("--notes", default=None)
    organizer_update.set_defaults(func=command_organizer_update_block)

    organizer_list = organizer_sub.add_parser("list-projects", help="list organizer projects")
    organizer_list.add_argument("--json", action="store_true", help="print only raw projects json")
    organizer_list.set_defaults(func=command_organizer_list_projects)

    organizer_scan = organizer_sub.add_parser("scan-assets", help="scan project asset inbox and auto-mark generated blocks")
    organizer_scan.add_argument("--project-drawer", required=True)
    organizer_scan.set_defaults(func=command_organizer_scan_assets)

    organizer_refresh = organizer_sub.add_parser(
        "refresh-dependencies",
        help="recalculate block dependencies for a project timeline",
    )
    organizer_refresh.add_argument("--project-drawer", required=True)
    organizer_refresh.set_defaults(func=command_organizer_refresh_dependencies)

    return parser


def main():
    import uuid
    from datetime import datetime, timezone
    
    parser = build_parser()
    args = parser.parse_args()
    
    # Setup audit envelope
    command_id = str(uuid.uuid4())
    start_time = time.time()
    status = "success"
    error_details = None
    
    try:
        args.func(args)
    except Exception as e:
        status = "failure"
        error_details = str(e)
        raise
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        audit_record = {
            "command_id": command_id,
            "status": status,
            "evidence": {
                "command": sys.argv[1:],
            },
            "error_details": error_details,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_ms": duration_ms
            }
        }
        
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        audit_log = LOG_DIR / "audit_envelope.jsonl"
        with open(audit_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(audit_record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
