import json
from datetime import datetime
from pathlib import Path


def _load(path: Path) -> dict:
    if not path.exists():
        return {"version": "1.0", "concepts": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": "1.0", "concepts": []}


def _save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def list_concepts(path: Path) -> list[dict]:
    db = _load(path)
    return db.get("concepts", [])


def upsert_concept(path: Path, name: str, hypothesis: str, status: str, evidence: str) -> dict:
    db = _load(path)
    concepts = db.setdefault("concepts", [])
    now = datetime.now().isoformat(timespec="seconds")

    existing = next((c for c in concepts if c.get("name") == name), None)
    if existing:
        existing["hypothesis"] = hypothesis
        existing["status"] = status
        existing["evidence"] = evidence
        existing["updated_at"] = now
        concept = existing
    else:
        concept = {
            "name": name,
            "hypothesis": hypothesis,
            "status": status,
            "evidence": evidence,
            "created_at": now,
            "updated_at": now,
        }
        concepts.append(concept)

    _save(path, db)
    return concept
