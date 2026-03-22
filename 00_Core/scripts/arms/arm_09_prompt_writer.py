import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from arms.ai_engine import generate_with_active_provider
from arms.hcb_identity import load_active_user_context


TARGET_PROFILES = {
    "midjourney": {
        "artifact_type": "image",
        "workflow_lane": "visual",
        "suggested_track": "V1",
        "project_domain": "media",
        "workflow_type": "media_production",
        "unit_type": "media_block",
        "default_language": "en",
        "rule_hint": "Use vivid visual keywords, composition, camera, lighting, and Midjourney parameters.",
    },
    "elevenlabs": {
        "artifact_type": "speech",
        "workflow_lane": "audio",
        "suggested_track": "A1",
        "project_domain": "media",
        "workflow_type": "media_production",
        "unit_type": "media_block",
        "default_language": "en",
        "rule_hint": "Write speakable lines with pacing, emphasis, pauses, and delivery cues.",
    },
    "suno": {
        "artifact_type": "audio",
        "workflow_lane": "audio",
        "suggested_track": "A3",
        "project_domain": "media",
        "workflow_type": "media_production",
        "unit_type": "media_block",
        "default_language": "en",
        "rule_hint": "Describe genre, mood, tempo, instrumentation, and song structure.",
    },
    "runway": {
        "artifact_type": "video",
        "workflow_lane": "visual",
        "suggested_track": "V1",
        "project_domain": "media",
        "workflow_type": "media_production",
        "unit_type": "media_block",
        "default_language": "en",
        "rule_hint": "Describe motion, camera movement, scene continuity, style, and timing.",
    },
    "generic": {
        "artifact_type": "text",
        "workflow_lane": "instruction",
        "suggested_track": "V2",
        "project_domain": "general",
        "workflow_type": "general_flow",
        "unit_type": "instruction_block",
        "default_language": "en",
        "rule_hint": "Provide clear instruction, context, constraints, and desired output format.",
    },
}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _resolve_target_profile(target_tool: str, language: str) -> dict:
    key = (target_tool or "").strip().lower()
    profile = TARGET_PROFILES.get(key, TARGET_PROFILES["generic"]).copy()
    profile["target_tool"] = key or "generic"
    profile["language"] = language or profile["default_language"]
    return profile


def _slugify(value: str, fallback: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower())
    text = text.strip("_")
    return text or fallback


def _infer_workflow_lane(artifact_type: str) -> str:
    mapping = {
        "image": "visual",
        "video": "visual",
        "speech": "audio",
        "audio": "audio",
        "graphic": "evidence",
        "checklist": "support",
        "task": "execution",
        "text": "instruction",
        "note": "instruction",
        "table": "evidence",
    }
    return mapping.get((artifact_type or "").strip().lower(), "instruction")


def _infer_unit_type(artifact_type: str, workflow_type: str) -> str:
    artifact = (artifact_type or "").strip().lower()
    workflow = (workflow_type or "").strip().lower()
    if workflow == "teaching_flow":
        return "teaching_block"
    if workflow == "research_flow":
        return "evidence_block" if artifact in {"graphic", "table", "text", "note"} else "planning_block"
    if workflow == "assistive_flow":
        return "assistive_block"
    if workflow == "business_flow":
        return "planning_block" if artifact in {"text", "table", "task"} else "support_block"
    if workflow == "home_flow":
        return "support_block"
    if artifact in {"image", "video", "audio", "speech"}:
        return "media_block"
    return "instruction_block"


def _infer_expected_output(artifact_type: str, target_tool: str) -> str:
    artifact = (artifact_type or "").strip().lower()
    tool = (target_tool or "").strip().lower()
    descriptions = {
        "image": "Imagem pronta para uso, coerente com o prompt e adequada para a ferramenta de destino.",
        "video": "Video gerado com movimento, continuidade e estilo compatíveis com a intencao declarada.",
        "audio": "Audio final gerado com identidade sonora coerente e pronto para organizacao no projeto.",
        "speech": "Narracao ou fala gerada com clareza, ritmo e intencao adequados.",
        "text": "Texto estruturado e utilizavel sem reescrita estrutural.",
        "graphic": "Grafico ou visual explicativo claro, conferivel e reaproveitavel.",
        "checklist": "Checklist operacional pronta para execucao e revisao.",
        "table": "Tabela organizada com colunas e informacao conferivel.",
        "note": "Nota resumida, objetiva e rastreavel.",
        "task": "Tarefa operacional clara, acionavel e verificavel.",
    }
    return f"{descriptions.get(artifact, 'Artefato pronto para uso operacional.')} Ferramenta alvo: {tool or 'generic'}."


def _build_operational_context(
    config_path: Path,
    profile: dict,
    *,
    project_drawer: str | None,
    project_domain: str | None,
    workflow_type: str | None,
    workflow_lane: str | None,
    sequence_label: str | None,
    sequence_index: int,
    unit_type: str | None,
    phase: str | None,
    insertion_mode: str | None,
    revision_of: str | None,
) -> dict:
    root = config_path.resolve().parents[2]
    context = load_active_user_context(root) or {}
    sci = context.get("sci") or {}
    state = context.get("state") or {}
    identity_base = sci.get("identity_base") or {}

    resolved_project_drawer = (
        project_drawer
        or state.get("active_project")
        or "projeto_geral"
    )
    resolved_project_domain = project_domain or profile["project_domain"]
    resolved_workflow_type = workflow_type or profile["workflow_type"]
    resolved_workflow_lane = workflow_lane or profile["workflow_lane"] or _infer_workflow_lane(profile["artifact_type"])
    resolved_sequence_label = sequence_label or "principal"
    resolved_sequence_index = max(sequence_index or 0, 0)
    resolved_unit_type = unit_type or profile["unit_type"] or _infer_unit_type(profile["artifact_type"], resolved_workflow_type)
    resolved_phase = phase or "generate"
    resolved_insertion_mode = insertion_mode or "append"

    sequence_slug = _slugify(resolved_sequence_label, "principal")
    sequence_id = f"seq_{resolved_sequence_index:03d}_{sequence_slug}"
    unit_uuid = uuid.uuid4().hex[:8]
    unit_id = f"unit_{resolved_sequence_index:03d}_{sequence_slug}_{unit_uuid}"
    artifact_id = f"artifact_{unit_uuid}"

    return {
        "user_id": context.get("user_id", ""),
        "mode": state.get("mode", ""),
        "role_profile": identity_base.get("role_profile", ""),
        "active_project": state.get("active_project", ""),
        "project_id": _slugify(resolved_project_drawer, "projeto_geral"),
        "project_drawer": resolved_project_drawer,
        "project_domain": resolved_project_domain,
        "workflow_type": resolved_workflow_type,
        "workflow_lane": resolved_workflow_lane,
        "track": profile["suggested_track"],
        "sequence_id": sequence_id,
        "sequence_label": resolved_sequence_label,
        "sequence_index": resolved_sequence_index,
        "unit_id": unit_id,
        "unit_type": resolved_unit_type,
        "phase": resolved_phase,
        "artifact_id": artifact_id,
        "artifact_type": profile["artifact_type"],
        "target_tool": profile["target_tool"],
        "expected_output": _infer_expected_output(profile["artifact_type"], profile["target_tool"]),
        "expected_asset_match": {
            "id": artifact_id,
            "filename_prefix": unit_id,
            "artifact_type": profile["artifact_type"],
        },
        "dependency_targets": [],
        "insertion_mode": resolved_insertion_mode,
        "revision_of": revision_of,
    }


def _build_system_prompt(profile: dict) -> str:
    return f"""
You are the HCB Studio Arm 09 Universal Prompt Writer.
Convert a raw creative idea into a production-ready prompt for {profile["target_tool"]}.

Output language must be {profile["language"]}.
Artifact type must be {profile["artifact_type"]}.
Suggested timeline track is {profile["suggested_track"]}.

Tool-specific rule:
{profile["rule_hint"]}

Return ONLY a valid JSON object with this exact structure:
{{
  "artifact_type": "<text|speech|image|video|audio|graphic|checklist|table|note|task>",
  "prompt_oficial": "<detailed copy-paste-ready prompt>",
  "prompt_curto": "<short quick-test version>",
  "checklist_validacao": [
    "<check 1>",
    "<check 2>",
    "<check 3>"
  ],
  "observacoes_operacionais": "<brief usage note for the creator>"
}}
""".strip()


def _extract_json_payload(raw_text: str) -> dict:
    clean_text = (raw_text or "").strip()
    if clean_text.startswith("```"):
        lines = clean_text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean_text = "\n".join(lines).strip()
    return json.loads(clean_text)


def _fallback_payload(idea: str, profile: dict, raw_text: str, error: Exception) -> dict:
    return {
        "artifact_type": profile["artifact_type"],
        "prompt_oficial": idea,
        "prompt_curto": idea[:240],
        "checklist_validacao": [
            "Confirmar aderencia ao objetivo do bloco",
            "Confirmar idioma da ferramenta alvo",
            "Confirmar se o prompt pode ser colado sem ajuste estrutural",
        ],
        "observacoes_operacionais": f"Fallback acionado por erro de parse: {error}",
        "raw_response": raw_text,
    }


def _normalize_payload(base_payload: dict, idea: str, profile: dict, operational_context: dict) -> dict:
    block_id = operational_context["unit_id"]
    official = (base_payload.get("prompt_oficial") or idea).strip()
    short = (base_payload.get("prompt_curto") or official[:240]).strip()
    checklist = base_payload.get("checklist_validacao") or [
        "Confirmar clareza do prompt",
        "Confirmar formato esperado pela ferramenta",
        "Confirmar aderencia ao bloco de producao",
    ]
    if not isinstance(checklist, list):
        checklist = [str(checklist)]

    artifact_type = base_payload.get("artifact_type") or base_payload.get("tipo_de_ativo") or operational_context["artifact_type"]

    return {
        "schema_version": "2.0",
        "block_id": block_id,
        "created_at": _utc_now(),
        "source_arm": "arm_09_prompt_writer",
        "status": "prompt_pronto",
        "estado": "prompt_pronto",
        "user_id": operational_context["user_id"],
        "mode": operational_context["mode"],
        "role_profile": operational_context["role_profile"],
        "active_project": operational_context["active_project"],
        "project_id": operational_context["project_id"],
        "project_drawer": operational_context["project_drawer"],
        "project_domain": operational_context["project_domain"],
        "workflow_type": operational_context["workflow_type"],
        "workflow_lane": operational_context["workflow_lane"],
        "track": operational_context["track"],
        "sequence_id": operational_context["sequence_id"],
        "sequence_label": operational_context["sequence_label"],
        "sequence_index": operational_context["sequence_index"],
        "unit_id": operational_context["unit_id"],
        "unit_type": operational_context["unit_type"],
        "unit_goal": idea,
        "phase": operational_context["phase"],
        "source_idea": idea,
        "artifact_id": operational_context["artifact_id"],
        "artifact_type": artifact_type,
        "tipo_de_ativo": artifact_type,
        "target_tool": profile["target_tool"],
        "ferramenta_destino": profile["target_tool"],
        "idioma_prompt": profile["language"],
        "prompt_oficial": official,
        "prompt_curto": short,
        "expected_output": operational_context["expected_output"],
        "expected_asset_match": {
            **operational_context["expected_asset_match"],
            "artifact_type": artifact_type,
        },
        "dependency_targets": operational_context["dependency_targets"],
        "insertion_mode": operational_context["insertion_mode"],
        "revision_of": operational_context["revision_of"],
        "checklist_validacao": checklist,
        "observacoes_operacionais": base_payload.get("observacoes_operacionais", ""),
        "organizer_hint": {
            "workflow_lane": operational_context["workflow_lane"],
            "suggested_track": operational_context["track"],
            "asset_type": artifact_type,
            "status": "prompt_pronto",
            "next_arm": "arm_10_block_organizer",
        },
        "timeline_stub": {
            "block_id": block_id,
            "unit_id": operational_context["unit_id"],
            "sequence_id": operational_context["sequence_id"],
            "workflow_lane": operational_context["workflow_lane"],
            "track": operational_context["track"],
            "in_point_ms": 0,
            "out_point_ms": 0,
            "file_reference": "",
            "prompt_origin_id": block_id,
            "status": "prompt_pronto",
        },
    }


def validate_prompt_block(payload: dict) -> list[str]:
    issues = []
    required = [
        "schema_version",
        "created_at",
        "status",
        "user_id",
        "project_drawer",
        "project_domain",
        "workflow_type",
        "workflow_lane",
        "sequence_id",
        "sequence_label",
        "sequence_index",
        "unit_id",
        "unit_type",
        "unit_goal",
        "phase",
        "artifact_type",
        "target_tool",
        "prompt_oficial",
        "prompt_curto",
        "expected_output",
        "expected_asset_match",
        "dependency_targets",
        "insertion_mode",
        "timeline_stub",
    ]
    for key in required:
        if key not in payload or payload[key] in ("", None):
            issues.append(f"missing_or_empty:{key}")

    workflow_lane = (((payload.get("timeline_stub") or {}).get("workflow_lane")) or "").strip()
    if workflow_lane not in {"instruction", "evidence", "visual", "audio", "review", "support", "planning", "execution"}:
        issues.append("invalid_workflow_lane")

    status = (((payload.get("timeline_stub") or {}).get("status")) or "").strip()
    if status != "prompt_pronto":
        issues.append("invalid_timeline_status")

    expected_asset_match = payload.get("expected_asset_match") or {}
    if not expected_asset_match.get("artifact_type"):
        issues.append("missing_expected_asset_match_artifact_type")

    return issues


def generate_production_prompts(
    config_path: Path,
    idea: str,
    target_tool: str,
    language: str = "en",
    *,
    project_drawer: str | None = None,
    project_domain: str | None = None,
    workflow_type: str | None = None,
    workflow_lane: str | None = None,
    sequence_label: str | None = None,
    sequence_index: int = 0,
    unit_type: str | None = None,
    phase: str | None = None,
    insertion_mode: str | None = None,
    revision_of: str | None = None,
) -> dict:
    profile = _resolve_target_profile(target_tool, language)
    operational_context = _build_operational_context(
        config_path,
        profile,
        project_drawer=project_drawer,
        project_domain=project_domain,
        workflow_type=workflow_type,
        workflow_lane=workflow_lane,
        sequence_label=sequence_label,
        sequence_index=sequence_index,
        unit_type=unit_type,
        phase=phase,
        insertion_mode=insertion_mode,
        revision_of=revision_of,
    )
    system_prompt = _build_system_prompt(profile)
    user_prompt = f"Raw idea:\n{idea.strip()}"

    result = generate_with_active_provider(
        config_path,
        prompt=user_prompt,
        system_prompt=system_prompt,
    )

    raw_text = result.get("text", "")
    try:
        parsed = _extract_json_payload(raw_text)
    except Exception as error:
        parsed = _fallback_payload(idea, profile, raw_text, error)

    payload = _normalize_payload(parsed, idea, profile, operational_context)
    payload["validation_issues"] = validate_prompt_block(payload)
    payload["engine_trace"] = {
        "provider": result.get("provider"),
        "model": result.get("model"),
        "timestamp": result.get("timestamp"),
        "hcb_context_loaded": result.get("hcb_context_loaded", False),
    }
    return payload
