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

ARTIFACT_TYPES = {"text", "speech", "image", "video", "audio", "graphic", "checklist", "table", "note", "task"}
WORKFLOW_LANES = {"instruction", "evidence", "visual", "audio", "review", "support", "planning", "execution"}
MEDIA_TRACKS = {"V1", "V2", "A1", "A2", "A3"}


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


def _assets_dir(storage_dir: Path, project_drawer: str) -> Path:
    return _project_root(storage_dir, project_drawer) / "assets_inbox"


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
        "text": 0,
        "speech": 0,
        "image": 0,
        "video": 0,
        "audio": 0,
        "graphic": 0,
        "checklist": 0,
        "table": 0,
        "note": 0,
        "task": 0,
    }


def _infer_project_domain(name: str, goal: str) -> str:
    haystack = f"{name} {goal}".lower()
    if any(token in haystack for token in {"aula", "curso", "aluno", "escola", "teacher", "faculdade"}):
        return "education"
    if any(token in haystack for token in {"pesquisa", "cient", "artigo", "hipotese", "experimento", "cern"}):
        return "science"
    if any(token in haystack for token in {"empresa", "cliente", "onboarding", "relatorio", "negocio"}):
        return "business"
    if any(token in haystack for token in {"casa", "compras", "receita", "mercado", "rotina"}):
        return "home"
    if any(token in haystack for token in {"assistivo", "assistencia", "tetra", "alzheimer", "limitacao", "acompanhamento"}):
        return "assistive"
    if any(token in haystack for token in {"video", "youtube", "capcut", "roteiro", "cena", "storyboard"}):
        return "media"
    return "general"


def _workflow_from_domain(project_domain: str) -> str:
    mapping = {
        "media": "media_production",
        "education": "teaching_flow",
        "science": "research_flow",
        "business": "business_flow",
        "home": "home_flow",
        "assistive": "assistive_flow",
        "general": "general_flow",
    }
    return mapping.get((project_domain or "").strip().lower(), "general_flow")


def _infer_workflow_lane_from_artifact(artifact_type: str) -> str:
    mapping = {
        "text": "instruction",
        "note": "instruction",
        "table": "evidence",
        "graphic": "evidence",
        "speech": "audio",
        "audio": "audio",
        "image": "visual",
        "video": "visual",
        "checklist": "support",
        "task": "execution",
    }
    return mapping.get((artifact_type or "").strip().lower(), "instruction")


def _infer_semantic_role(block: dict, project_domain: str) -> str:
    artifact_type = (block.get("artifact_type") or block.get("tipo_de_ativo") or "").strip()
    notes = (block.get("notes") or "").lower()
    target = (block.get("target_tool") or block.get("ferramenta_destino") or "").lower()
    unit_type = (block.get("unit_type") or "").strip()
    workflow_lane = (block.get("workflow_lane") or "").strip()

    if unit_type:
        return unit_type
    if workflow_lane:
        return workflow_lane

    if artifact_type == "text":
        if project_domain in {"education", "science"}:
            return "knowledge_base"
        return "script_base"
    if artifact_type == "speech":
        if "abertura" in notes or "intro" in notes:
            return "narration_intro"
        if project_domain in {"education", "science"}:
            return "explanation_voice"
        return "narration_voice"
    if artifact_type in {"image", "video", "graphic"}:
        if any(token in notes for token in {"grafico", "chart", "diagrama"}):
            return "evidence_visual"
        if project_domain == "business":
            return "presentation_visual"
        return "support_visual"
    if artifact_type == "audio":
        if target == "suno" or any(token in notes for token in {"trilha", "music", "musica"}):
            return "music_bed"
        return "sound_design"
    return "generic_asset"


def _ensure_sequence_entry(timeline: dict, block: dict) -> None:
    sequence_id = block.get("sequence_id")
    if not sequence_id:
        return
    sequences = timeline.setdefault("sequences", [])
    if any(item.get("sequence_id") == sequence_id for item in sequences):
        return
    sequences.append(
        {
            "sequence_id": sequence_id,
            "sequence_label": block.get("sequence_label", sequence_id),
            "sequence_index": int(block.get("sequence_index", 0) or 0),
            "phase": block.get("phase", ""),
            "status": block.get("status", "draft"),
        }
    )
    sequences.sort(key=lambda item: (int(item.get("sequence_index", 0)), item.get("sequence_label", "")))


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
    _assets_dir(storage_dir, project_drawer).mkdir(parents=True, exist_ok=True)

    timeline = {
        "schema_version": "2.0",
        "project_id": project_id,
        "project_drawer": project_drawer,
        "project_domain": _infer_project_domain(name, goal),
        "workflow_type": _workflow_from_domain(_infer_project_domain(name, goal)),
        "nome": name,
        "objetivo": goal,
        "estado_global": "draft",
        "created_at": now,
        "updated_at": now,
        "timeline_policy": {
            "placement_mode": "automatico",
            "export_intent": "json_interno",
            "revision_policy": "tracked",
        },
        "sequences": [],
        "blocks": [],
    }
    project = {
        "project_id": project_id,
        "project_drawer": project_drawer,
        "nome": name,
        "objetivo": goal,
        "domain_profile": _infer_project_domain(name, goal),
        "estado_global": "draft",
        "created_at": now,
        "updated_at": now,
        "assets_summary": _empty_assets_summary(),
        "timeline_file": str(_timeline_file(storage_dir, project_drawer)),
        "block_queue_dir": str(_blocks_dir(storage_dir, project_drawer)),
        "assets_inbox_dir": str(_assets_dir(storage_dir, project_drawer)),
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
        artifact_type = block.get("artifact_type") or block.get("tipo_de_ativo")
        if artifact_type in summary:
            summary[artifact_type] += 1
    return summary


def _track_priority(block: dict) -> tuple[int, int]:
    asset_order = {"text": 0, "note": 0, "table": 0, "speech": 1, "image": 2, "video": 2, "graphic": 2, "audio": 3}
    order = {"A1": 0, "V2": 1, "V1": 2, "A2": 3, "A3": 4}
    asset_type = (block.get("artifact_type") or block.get("tipo_de_ativo") or "").strip()
    track = (block.get("track") or "").strip()
    sequence_index = int(block.get("sequence_index", 0) or 0)
    return (sequence_index, asset_order.get(asset_type, 99), order.get(track, 99), int(block.get("in_point_ms", 0)))


def _is_ready_dependency_candidate(block: dict) -> bool:
    return block.get("status") not in {"descartado", ""}


def infer_block_dependencies(blocks: list[dict], project_domain: str = "general") -> list[dict]:
    ordered = sorted(blocks, key=_track_priority)
    latest_by_role_by_sequence: dict[str, dict[str, str]] = {}

    for block in ordered:
        if not _is_ready_dependency_candidate(block):
            block["dependency_targets"] = []
            block["dependencies"] = []
            block["dependency_reason"] = ""
            continue

        explicit_dependencies = block.get("dependency_targets") or []
        if explicit_dependencies:
            block["dependencies"] = explicit_dependencies
            block["dependency_reason"] = "explicit_dependency_targets"
            sequence_key = block.get("sequence_id") or "__global__"
            latest_by_role_by_sequence.setdefault(sequence_key, {})[_infer_semantic_role(block, project_domain)] = block["block_id"]
            continue

        sequence_key = block.get("sequence_id") or "__global__"
        latest_by_role = latest_by_role_by_sequence.setdefault(sequence_key, {})
        semantic_role = _infer_semantic_role(block, project_domain)
        artifact_type = (block.get("artifact_type") or block.get("tipo_de_ativo") or "").strip()
        dependencies = []
        dependency_reason = ""

        if semantic_role in {"knowledge_base", "script_base"}:
            dependencies = []
            dependency_reason = "base_block"
        elif semantic_role in {"narration_intro", "narration_voice", "explanation_voice"}:
            base_text = latest_by_role.get("knowledge_base") or latest_by_role.get("script_base")
            if base_text:
                dependencies.append(base_text)
                dependency_reason = "voice_depends_on_textual_base"
        elif semantic_role in {"support_visual", "presentation_visual", "evidence_visual"}:
            speech_base = (
                latest_by_role.get("explanation_voice")
                or latest_by_role.get("narration_voice")
                or latest_by_role.get("narration_intro")
            )
            text_base = latest_by_role.get("knowledge_base") or latest_by_role.get("script_base")
            if speech_base:
                dependencies.append(speech_base)
                dependency_reason = "visual_syncs_with_voice"
            elif text_base:
                dependencies.append(text_base)
                dependency_reason = "visual_depends_on_textual_base"
        elif semantic_role in {"music_bed", "sound_design"}:
            speech_base = (
                latest_by_role.get("explanation_voice")
                or latest_by_role.get("narration_voice")
                or latest_by_role.get("narration_intro")
            )
            visual_base = (
                latest_by_role.get("support_visual")
                or latest_by_role.get("presentation_visual")
                or latest_by_role.get("evidence_visual")
            )
            if speech_base:
                dependencies.append(speech_base)
                dependency_reason = "audio_layer_follows_voice"
            elif visual_base:
                dependencies.append(visual_base)
                dependency_reason = "audio_layer_follows_visual"
        elif artifact_type == "speech":
            text_base = latest_by_role.get("knowledge_base") or latest_by_role.get("script_base")
            if text_base:
                dependencies.append(text_base)
                dependency_reason = "speech_depends_on_text"

        block["semantic_role"] = semantic_role
        block["dependency_targets"] = dependencies
        block["dependencies"] = dependencies
        block["dependency_reason"] = dependency_reason
        latest_by_role[semantic_role] = block["block_id"]

    return blocks


def _normalize_block_for_timeline(prompt_block: dict) -> dict:
    timeline_stub = prompt_block.get("timeline_stub", {})
    artifact_type = prompt_block.get("artifact_type") or prompt_block.get("tipo_de_ativo") or "text"
    workflow_lane = prompt_block.get("workflow_lane") or timeline_stub.get("workflow_lane") or _infer_workflow_lane_from_artifact(artifact_type)
    sequence_id = prompt_block.get("sequence_id") or timeline_stub.get("sequence_id") or "seq_000_principal"
    sequence_label = prompt_block.get("sequence_label") or "principal"
    sequence_index = int(prompt_block.get("sequence_index", 0) or 0)
    unit_id = prompt_block.get("unit_id") or prompt_block.get("block_id")
    target_tool = prompt_block.get("target_tool") or prompt_block.get("ferramenta_destino") or ""
    return {
        "block_id": prompt_block["block_id"],
        "prompt_origin_id": prompt_block["block_id"],
        "user_id": prompt_block.get("user_id", ""),
        "mode": prompt_block.get("mode", ""),
        "workflow_lane": workflow_lane,
        "track": timeline_stub.get("track", prompt_block.get("track", prompt_block.get("organizer_hint", {}).get("suggested_track", "V2"))),
        "sequence_id": sequence_id,
        "sequence_label": sequence_label,
        "sequence_index": sequence_index,
        "unit_id": unit_id,
        "unit_type": prompt_block.get("unit_type", ""),
        "unit_goal": prompt_block.get("unit_goal") or prompt_block.get("source_idea", ""),
        "phase": prompt_block.get("phase", "generate"),
        "artifact_id": prompt_block.get("artifact_id", ""),
        "artifact_type": artifact_type,
        "tipo_de_ativo": artifact_type,
        "target_tool": target_tool,
        "ferramenta_destino": target_tool,
        "expected_output": prompt_block.get("expected_output", ""),
        "expected_asset_match": prompt_block.get("expected_asset_match") or {"artifact_type": artifact_type},
        "in_point_ms": int(timeline_stub.get("in_point_ms", 0)),
        "out_point_ms": int(timeline_stub.get("out_point_ms", 0)),
        "file_reference": timeline_stub.get("file_reference", ""),
        "status": timeline_stub.get("status", "prompt_pronto"),
        "dependency_targets": list(prompt_block.get("dependency_targets") or []),
        "dependencies": [],
        "dependency_reason": "",
        "revision_of": prompt_block.get("revision_of"),
        "revision_reason": prompt_block.get("revision_reason", ""),
        "insertion_mode": prompt_block.get("insertion_mode", "append"),
        "supersedes": None,
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

    candidates = sorted(queue_dir.glob("*.json"))
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
        _ensure_sequence_entry(timeline, timeline_block)
        infer_block_dependencies(timeline["blocks"], project.get("domain_profile", "general"))
        existing_ids.add(current_id)
        ingested.append(
            {
                "block_id": current_id,
                "artifact_type": timeline_block["artifact_type"],
                "workflow_lane": timeline_block["workflow_lane"],
                "track": timeline_block["track"],
                "dependency_targets": timeline_block["dependency_targets"],
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
    if track and track not in MEDIA_TRACKS:
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

    infer_block_dependencies(timeline["blocks"], project.get("domain_profile", "general"))
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


def refresh_dependencies(storage_dir: Path, project_drawer: str) -> dict:
    project = load_project(storage_dir, project_drawer)
    timeline = load_timeline(storage_dir, project_drawer)
    if not project.get("domain_profile"):
        project["domain_profile"] = _infer_project_domain(project.get("nome", ""), project.get("objetivo", ""))
    infer_block_dependencies(timeline["blocks"], project.get("domain_profile", "general"))
    project["assets_summary"] = _count_assets(timeline["blocks"])
    _save_project_and_timeline(storage_dir, project_drawer, project, timeline)
    return {
        "project_drawer": project_drawer,
        "domain_profile": project.get("domain_profile", "general"),
        "blocks": [
            {
                "block_id": block.get("block_id"),
                "semantic_role": block.get("semantic_role", ""),
                "dependency_targets": block.get("dependency_targets", []),
                "dependencies": block.get("dependencies", []),
                "dependency_reason": block.get("dependency_reason", ""),
                "workflow_lane": block.get("workflow_lane", ""),
                "sequence_id": block.get("sequence_id", ""),
                "track": block.get("track"),
                "status": block.get("status"),
            }
            for block in timeline.get("blocks", [])
        ],
    }


def scan_generated_assets(storage_dir: Path, project_drawer: str) -> dict:
    project = load_project(storage_dir, project_drawer)
    timeline = load_timeline(storage_dir, project_drawer)
    inbox_dir = _assets_dir(storage_dir, project_drawer)
    inbox_dir.mkdir(parents=True, exist_ok=True)

    files = [path for path in inbox_dir.iterdir() if path.is_file()]
    matched = []

    for block in timeline.get("blocks", []):
        if block.get("status") not in {"prompt_pronto", "executando", "revisao"}:
            continue

        block_id = block.get("block_id", "")
        prompt_origin_id = block.get("prompt_origin_id", "")
        expected_match = block.get("expected_asset_match") or {}
        expected_id = (expected_match.get("id") or "").strip()
        expected_prefix = (expected_match.get("filename_prefix") or "").strip()
        expected_artifact_type = (expected_match.get("artifact_type") or block.get("artifact_type") or "").strip().lower()
        file_match = next(
            (
                path
                for path in files
                if (
                    (expected_id and expected_id in path.stem)
                    or (expected_prefix and path.stem.startswith(expected_prefix))
                    or (
                        expected_artifact_type
                        and path.stem == block_id
                        and expected_artifact_type == (block.get("artifact_type") or "").strip().lower()
                    )
                    or (not expected_id and not expected_prefix and (block_id and block_id in path.name or (prompt_origin_id and prompt_origin_id in path.name)))
                )
            ),
            None,
        )

        if not file_match:
            continue

        block["file_reference"] = str(file_match)
        block["status"] = "gerado"
        if not block.get("source_ai"):
            block["source_ai"] = block.get("target_tool") or block.get("ferramenta_destino", "")
        matched.append(
            {
                "block_id": block_id,
                "file_reference": str(file_match),
                "status": block["status"],
            }
        )

    if matched:
        timeline["estado_global"] = "ativo"
        project["estado_global"] = "ativo"
        infer_block_dependencies(timeline["blocks"], project.get("domain_profile", "general"))
        project["assets_summary"] = _count_assets(timeline["blocks"])
        _save_project_and_timeline(storage_dir, project_drawer, project, timeline)

    return {
        "project_drawer": project_drawer,
        "assets_inbox_dir": str(inbox_dir),
        "matched_count": len(matched),
        "matched_blocks": matched,
    }
