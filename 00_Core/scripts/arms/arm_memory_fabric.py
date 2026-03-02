import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def _capsule_dir(root: Path) -> Path:
    return root / "01_Archivus" / "capsules"


def _safe_slug(value: str) -> str:
    value = (value or "capsule").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "capsule"


def save_capsule(root: Path, modulo: str, atividade: str, comentarios: str, ia_origem: str) -> Path:
    capsule_id = f"{_safe_slug(modulo)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    payload = {
        "id": capsule_id,
        "modulo": modulo,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "atividade": atividade,
        "comentarios": comentarios,
        "ia_origem": ia_origem,
        "contexto_adicional": {
            "source": "hcb_control_arm_memory",
            "schema_version": "1.0",
        },
    }

    target_dir = _capsule_dir(root)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{capsule_id}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def list_capsules(root: Path, limit: int = 20) -> list[dict]:
    target_dir = _capsule_dir(root)
    if not target_dir.exists():
        return []
    files = sorted(target_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    result = []
    for file in files:
        try:
            payload = json.loads(file.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        result.append(
            {
                "id": payload.get("id"),
                "modulo": payload.get("modulo"),
                "atividade": payload.get("atividade"),
                "timestamp": payload.get("timestamp"),
                "path": str(file),
            }
        )
    return result


def find_capsules(root: Path, query: str, limit: int = 20) -> list[dict]:
    q = (query or "").strip().lower()
    if not q:
        return []
    target_dir = _capsule_dir(root)
    if not target_dir.exists():
        return []

    matches = []
    for file in sorted(target_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        raw_text = file.read_text(encoding="utf-8", errors="ignore")
        if q in raw_text.lower():
            try:
                payload = json.loads(raw_text)
            except Exception:
                payload = {}
            matches.append(
                {
                    "id": payload.get("id"),
                    "modulo": payload.get("modulo"),
                    "atividade": payload.get("atividade"),
                    "timestamp": payload.get("timestamp"),
                    "path": str(file),
                }
            )
            if len(matches) >= limit:
                break
    return matches
