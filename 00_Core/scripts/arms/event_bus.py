import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def append_event(event_log_path: Path, event_type: str, payload: dict) -> dict:
    event_log_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event_id": uuid4().hex,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event_type": event_type,
        "payload": payload,
    }
    with event_log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def read_recent_events(event_log_path: Path, limit: int = 20) -> list[dict]:
    if not event_log_path.exists():
        return []
    lines = event_log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    out = []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
        if len(out) >= limit:
            break
    return out
