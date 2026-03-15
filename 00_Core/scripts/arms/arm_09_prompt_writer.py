import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from arms.ai_engine import generate_with_active_provider


TARGET_PROFILES = {
    "midjourney": {
        "asset_type": "image",
        "suggested_track": "V1",
        "default_language": "en",
        "rule_hint": "Use vivid visual keywords, composition, camera, lighting, and Midjourney parameters.",
    },
    "elevenlabs": {
        "asset_type": "speech",
        "suggested_track": "A1",
        "default_language": "en",
        "rule_hint": "Write speakable lines with pacing, emphasis, pauses, and delivery cues.",
    },
    "suno": {
        "asset_type": "audio",
        "suggested_track": "A3",
        "default_language": "en",
        "rule_hint": "Describe genre, mood, tempo, instrumentation, and song structure.",
    },
    "runway": {
        "asset_type": "video",
        "suggested_track": "V1",
        "default_language": "en",
        "rule_hint": "Describe motion, camera movement, scene continuity, style, and timing.",
    },
    "generic": {
        "asset_type": "text",
        "suggested_track": "V2",
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


def _build_system_prompt(profile: dict) -> str:
    return f"""
You are the HCB Studio Arm 09 Universal Prompt Writer.
Convert a raw creative idea into a production-ready prompt for {profile["target_tool"]}.

Output language must be {profile["language"]}.
Asset type must be {profile["asset_type"]}.
Suggested timeline track is {profile["suggested_track"]}.

Tool-specific rule:
{profile["rule_hint"]}

Return ONLY a valid JSON object with this exact structure:
{{
  "tipo_de_ativo": "<image|video|audio|speech|text>",
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
        "tipo_de_ativo": profile["asset_type"],
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


def _normalize_payload(base_payload: dict, idea: str, profile: dict) -> dict:
    block_id = f"blk_{uuid.uuid4().hex[:8]}"
    official = (base_payload.get("prompt_oficial") or idea).strip()
    short = (base_payload.get("prompt_curto") or official[:240]).strip()
    checklist = base_payload.get("checklist_validacao") or [
        "Confirmar clareza do prompt",
        "Confirmar formato esperado pela ferramenta",
        "Confirmar aderencia ao bloco de producao",
    ]
    if not isinstance(checklist, list):
        checklist = [str(checklist)]

    return {
        "block_id": block_id,
        "created_at": _utc_now(),
        "source_arm": "arm_09_prompt_writer",
        "estado": "prompt_pronto",
        "source_idea": idea,
        "tipo_de_ativo": base_payload.get("tipo_de_ativo") or profile["asset_type"],
        "ferramenta_destino": profile["target_tool"],
        "idioma_prompt": profile["language"],
        "prompt_oficial": official,
        "prompt_curto": short,
        "checklist_validacao": checklist,
        "observacoes_operacionais": base_payload.get("observacoes_operacionais", ""),
        "organizer_hint": {
            "suggested_track": profile["suggested_track"],
            "asset_type": base_payload.get("tipo_de_ativo") or profile["asset_type"],
            "status": "prompt_pronto",
            "next_arm": "arm_10_block_organizer",
        },
        "timeline_stub": {
            "block_id": block_id,
            "track": profile["suggested_track"],
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
        "block_id",
        "created_at",
        "estado",
        "source_idea",
        "tipo_de_ativo",
        "ferramenta_destino",
        "idioma_prompt",
        "prompt_oficial",
        "prompt_curto",
        "organizer_hint",
        "timeline_stub",
    ]
    for key in required:
        if key not in payload or payload[key] in ("", None):
            issues.append(f"missing_or_empty:{key}")

    track = (((payload.get("timeline_stub") or {}).get("track")) or "").strip()
    if track not in {"V1", "V2", "A1", "A2", "A3"}:
        issues.append("invalid_track")

    status = (((payload.get("timeline_stub") or {}).get("status")) or "").strip()
    if status != "prompt_pronto":
        issues.append("invalid_timeline_status")

    return issues


def generate_production_prompts(
    config_path: Path,
    idea: str,
    target_tool: str,
    language: str = "en",
) -> dict:
    profile = _resolve_target_profile(target_tool, language)
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

    payload = _normalize_payload(parsed, idea, profile)
    payload["validation_issues"] = validate_prompt_block(payload)
    payload["engine_trace"] = {
        "provider": result.get("provider"),
        "model": result.get("model"),
        "timestamp": result.get("timestamp"),
    }
    return payload
