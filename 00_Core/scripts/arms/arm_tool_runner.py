import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _intent_to_command(intent: str) -> list[str]:
    text = (intent or "").strip().lower()
    if not text:
        return ["status"]
    if any(word in text for word in ("status", "saude", "health", "estado")):
        return ["status"]
    if any(word in text for word in ("treinar", "train", "modelo", "brain")):
        return ["train"]
    if any(word in text for word in ("triagem", "organizar", "classificar", "quarentena")):
        return ["triage", "--mode", "smart"]
    if any(word in text for word in ("napkin", "guardanapo", "checkpoint")):
        return ["napkin"]
    if any(word in text for word in ("evoluir", "pipeline", "ciclo")):
        return ["evolve", "--mode", "smart", "--cycles", "1"]
    return ["status"]


def build_tool_action(intent: str, control_script: Path) -> dict:
    args = _intent_to_command(intent)
    cmd = [sys.executable, str(control_script), *args]
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "intent": intent,
        "resolved_args": args,
        "command": cmd,
    }


def run_tool_action(action: dict, dry_run: bool = False) -> dict:
    command = action["command"]
    action["command_pretty"] = " ".join(shlex.quote(part) for part in command)
    action["dry_run"] = dry_run

    if dry_run:
        action["ok"] = True
        action["returncode"] = 0
        action["stdout"] = ""
        action["stderr"] = ""
        return action

    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    action["ok"] = completed.returncode == 0
    action["returncode"] = completed.returncode
    action["stdout"] = completed.stdout.strip()
    action["stderr"] = completed.stderr.strip()
    return action
