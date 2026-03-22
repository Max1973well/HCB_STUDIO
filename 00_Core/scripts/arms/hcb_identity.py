import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _users_root(root: Path) -> Path:
    return root / "01_Archivus" / "users"


def sci_profiles_dir(root: Path) -> Path:
    return _users_root(root) / "sci_profiles"


def hcb_states_dir(root: Path) -> Path:
    return _users_root(root) / "hcb_states"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def create_sci_profile(
    root: Path,
    user_id: str,
    display_name: str,
    primary_language: str,
    timezone_name: str,
    role_profile: str,
    technical_level: str,
    preferred_tone: str,
    response_depth: str,
    step_by_step: bool,
    correction_style: str,
    needs_adaptation: bool,
    visual_support: bool,
    motor_support: bool,
    fatigue_support: bool,
    accessibility_notes: str = "",
) -> Path:
    now = _utc_now()
    payload = {
        "user_id": user_id,
        "display_name": display_name,
        "version": "1.0",
        "created_at": now,
        "updated_at": now,
        "identity_base": {
            "primary_language": primary_language,
            "timezone": timezone_name,
            "role_profile": role_profile,
            "technical_level": technical_level,
        },
        "interaction_profile": {
            "preferred_tone": preferred_tone,
            "response_depth": response_depth,
            "step_by_step": bool(step_by_step),
            "correction_style": correction_style,
        },
        "accessibility_profile": {
            "needs_adaptation": bool(needs_adaptation),
            "visual_support": bool(visual_support),
            "motor_support": bool(motor_support),
            "fatigue_support": bool(fatigue_support),
            "notes": accessibility_notes,
        },
        "governance": {
            "recognition_required": True,
            "allow_capsules_on_transition_only": True,
            "sci_is_stable": True,
        },
    }
    out = sci_profiles_dir(root) / f"{user_id}.json"
    _write_json(out, payload)
    return out


def create_hcb_state(
    root: Path,
    user_id: str,
    mode: str,
    energy: str = "medium",
    focus: str = "normal",
    urgency: str = "medium",
    cognitive_load: str = "moderate",
    response_preference: str = "balanced",
    active_project: str = "",
    notes: str = "",
    fatigue_now: bool = False,
    pain_now: bool = False,
    visual_overload: bool = False,
    needs_pause: bool = False,
) -> Path:
    payload = {
        "user_id": user_id,
        "session_id": f"sess_{uuid.uuid4().hex[:10]}",
        "updated_at": _utc_now(),
        "mode": mode,
        "energy": energy,
        "focus": focus,
        "urgency": urgency,
        "cognitive_load": cognitive_load,
        "response_preference": response_preference,
        "accessibility_flags": {
            "fatigue_now": bool(fatigue_now),
            "pain_now": bool(pain_now),
            "visual_overload": bool(visual_overload),
            "needs_pause": bool(needs_pause),
        },
        "active_project": active_project,
        "notes": notes,
    }
    out = hcb_states_dir(root) / f"{user_id}.json"
    _write_json(out, payload)
    return out
