import argparse
import importlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMP_DIR = ROOT / "04_TEMP"
STORAGE_DIR = ROOT / "02_STORAGE"
ENGINES_DIR = ROOT / "00_Core" / "engines"
LOG_DIR = ROOT / "00_Core" / "logs"

SENTINEL_SRC = ROOT / "03_TRAINING" / "PRJ_02_SENTINEL" / "src"
NAPKIN_CHECKPOINT_DIR = Path(r"F:\PrimeiroProjetoTest\checkpoints")


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

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
