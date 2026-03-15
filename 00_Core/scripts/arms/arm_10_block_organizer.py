import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


VALID_BLOCK_STATUS = {
    "draft",
    "prompt_pronto",
    "executando",
    "gerado",
    "revisao",
    "aprovado",
    "concluido",
    "descartado",
}

ASSET_TYPES = {"image", "video", "audio", "speech", "text"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project_root(storage_dir: Path, project_drawer: str) -> Path:
    return storage_dir / "projects" / project_drawer


def _project_file(storage_dir: Path, project_drawer: str) -> Path:
    return _project_root(storage_dir, project_drawer) / "project.json"


def _timeline_file(storage_dir: Path, project_drawer: str) -> Path:
    return _project_root(storage_dir, project_drawer) / "timeline.json"


def _blocks_dir(storage_dir: Path, project_drawer: str) -> Path:
    return _project_root(storage_dir, project_drawer) / "blocks"


def _prompt_queue_dir(storage_dir: Path) -> Path:
    return storage_dir / "blocks" / "prompt_queue"


def _processed_queue_dir(storage_dir: Path) -> Path:
    return storage_dir / "blocks" / "processed"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _empty_assets_summary() -> dict:
    return {
        "image": 0,
        "video": 0,
        "audio": 0,
        "speech": 0,
        "text": 0,
    }


def create_project(
    storage_dir: Path,
    project_id: str,
    project_drawer: str,
    name: str,
    goal: str,
) -> dict:
    now = _utc_now()
    root = _project_root(storage_dir, project_drawer)
    root.mkdir(parents=True, exist_ok=True)
    _blocks_dir(storage_dir, project_drawer).mkdir(parents=True, exist_ok=True)

    timeline = {
        "project_id": project_id,
        "project_drawer": project_drawer,
        "nome": name,
        "objetivo": goal,
        "estado_global": "draft",
        "created_at": now,
        "updated_at": now,
        "timeline_policy": {
            "placement_mode": "automatico",
            "export_intent": "json_interno",
        },
        "blocks": [],
    }
    project = {
        "project_id": project_id,
        "project_drawer": project_drawer,
        "nome": name,
        "objetivo": goal,
        "estado_global": "draft",
        "created_at": now,
        "updated_at": now,
        "assets_summary": _empty_assets_summary(),
        "timeline_file": str(_timeline_file(storage_dir, project_drawer)),
        "block_queue_dir": str(_blocks_dir(storage_dir, project_drawer)),
        "export_targets": ["json_interno"],
    }

    _write_json(_project_file(storage_dir, project_drawer), project)
    _write_json(_timeline_file(storage_dir, project_drawer), timeline)
    return project


def load_project(storage_dir: Path, project_drawer: str) -> dict:
    path = _project_file(storage_dir, project_drawer)
    if not path.exists():
        raise FileNotFoundError(f"Project drawer not found: {project_drawer}")
    return _read_json(path)


def load_timeline(storage_dir: Path, project_drawer: str) -> dict:
    path = _timeline_file(storage_dir, project_drawer)
    if not path.exists():
        raise FileNotFoundError(f"Timeline not found for drawer: {project_drawer}")
    return _read_json(path)


def _save_project_and_timeline(storage_dir: Path, project_drawer: str, project: dict, timeline: dict) -> None:
    project["updated_at"] = _utc_now()
    timeline["updated_at"] = project["updated_at"]
    _write_json(_project_file(storage_dir, project_drawer), project)
    _write_json(_timeline_file(storage_dir, project_drawer), timeline)


def _count_assets(blocks: list[dict]) -> dict:
    summary = _empty_assets_summary()
    for block in blocks:
        asset_type = block.get("tipo_de_ativo")
        if asset_type in summary:
            summary[asset_type] += 1
    return summary


def _normalize_block_for_timeline(prompt_block: dict) -> dict:
    timeline_stub = prompt_block.get("timeline_stub", {})
    return {
        "block_id": prompt_block["block_id"],
        "prompt_origin_id": prompt_block["block_id"],
        "tipo_de_ativo": prompt_block["tipo_de_ativo"],
        "ferramenta_destino": prompt_block["ferramenta_destino"],
        "track": timeline_stub.get("track", prompt_block.get("organizer_hint", {}).get("suggested_track", "V2")),
        "in_point_ms": int(timeline_stub.get("in_point_ms", 0)),
        "out_point_ms": int(timeline_stub.get("out_point_ms", 0)),
        "file_reference": timeline_stub.get("file_reference", ""),
        "status": timeline_stub.get("status", "prompt_pronto"),
        "dependencies": [],
        "source_ai": "",
        "notes": prompt_block.get("observacoes_operacionais", ""),
    }


def ingest_prompt_blocks(storage_dir: Path, project_drawer: str, block_id: str | None = None) -> dict:
    queue_dir = _prompt_queue_dir(storage_dir)
    if not queue_dir.exists():
        raise FileNotFoundError("Prompt queue directory does not exist.")

    project = load_project(storage_dir, project_drawer)
    timeline = load_timeline(storage_dir, project_drawer)
    existing_ids = {block["block_id"] for block in timeline.get("blocks", [])}

    candidates = sorted(queue_dir.glob("blk_*.json"))
    if block_id:
        candidates = [path for path in candidates if path.stem == block_id]

    ingested = []
    processed_dir = _processed_queue_dir(storage_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    for path in candidates:
        payload = _read_json(path)
        current_id = payload.get("block_id")
        if not current_id or current_id in existing_ids:
            continue

        project_block_path = _blocks_dir(storage_dir, project_drawer) / path.name
        shutil.copy2(path, project_block_path)

        timeline_block = _normalize_block_for_timeline(payload)
        timeline["blocks"].append(timeline_block)
        existing_ids.add(current_id)
        ingested.append(
            {
                "block_id": current_id,
                "tipo_de_ativo": timeline_block["tipo_de_ativo"],
                "track": timeline_block["track"],
                "project_block_path": str(project_block_path),
            }
        )

        shutil.move(str(path), str(processed_dir / path.name))

    timeline["estado_global"] = "ativo" if timeline["blocks"] else timeline["estado_global"]
    project["estado_global"] = timeline["estado_global"]
    project["assets_summary"] = _count_assets(timeline["blocks"])
    _save_project_and_timeline(storage_dir, project_drawer, project, timeline)

    return {
        "project_drawer": project_drawer,
        "ingested_count": len(ingested),
        "ingested_blocks": ingested,
        "timeline_file": str(_timeline_file(storage_dir, project_drawer)),
    }


def update_block(
    storage_dir: Path,
    project_drawer: str,
    block_id: str,
    status: str | None = None,
    file_reference: str | None = None,
    track: str | None = None,
    in_point_ms: int | None = None,
    out_point_ms: int | None = None,
    source_ai: str | None = None,
    notes: str | None = None,
) -> dict:
    if status and status not in VALID_BLOCK_STATUS:
        raise ValueError(f"Invalid block status: {status}")
    if track and track not in {"V1", "V2", "A1", "A2", "A3"}:
        raise ValueError(f"Invalid track: {track}")

    project = load_project(storage_dir, project_drawer)
    timeline = load_timeline(storage_dir, project_drawer)

    target = next((block for block in timeline.get("blocks", []) if block.get("block_id") == block_id), None)
    if not target:
        raise FileNotFoundError(f"Block not found in project drawer {project_drawer}: {block_id}")

    if status is not None:
        target["status"] = status
    if file_reference is not None:
        target["file_reference"] = file_reference
    if track is not None:
        target["track"] = track
    if in_point_ms is not None:
        target["in_point_ms"] = int(in_point_ms)
    if out_point_ms is not None:
        target["out_point_ms"] = int(out_point_ms)
    if source_ai is not None:
        target["source_ai"] = source_ai
    if notes is not None:
        target["notes"] = notes

    if any(block.get("status") == "concluido" for block in timeline["blocks"]):
        timeline["estado_global"] = "ativo"
        project["estado_global"] = "ativo"

    project["assets_summary"] = _count_assets(timeline["blocks"])
    _save_project_and_timeline(storage_dir, project_drawer, project, timeline)
    return target


def list_projects(storage_dir: Path) -> list[dict]:
    projects_dir = storage_dir / "projects"
    if not projects_dir.exists():
        return []
    results = []
    for project_file in sorted(projects_dir.glob("*/project.json")):
        try:
            results.append(_read_json(project_file))
        except Exception:
            continue
    return results
