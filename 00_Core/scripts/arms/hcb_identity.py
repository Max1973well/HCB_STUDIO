import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCI_ONBOARDING_QUESTIONS = [
    "1. Nome de exibição do usuário",
    "2. Idioma principal (ex.: pt-BR)",
    "3. Fuso horário (ex.: Europe/London)",
    "4. Perfil principal de uso: general|creator|student|teacher|researcher|business|developer",
    "5. Nível técnico: beginner|intermediate|advanced",
    "6. Tom preferido: direct|balanced|gentle",
    "7. Profundidade de resposta: short|balanced|deep",
    "8. Precisa de passo a passo? yes|no",
    "9. Estilo de correção: explicit|gentle|mixed",
    "10. Precisa de adaptação? yes|no",
    "11. Suporte visual? yes|no",
    "12. Suporte motor? yes|no",
    "13. Suporte para fadiga? yes|no",
    "14. Observações de acessibilidade (opcional)",
]

HCB_STATE_QUESTIONS = [
    "1. Modo atual: study|work|creation|research|review|support",
    "2. Energia agora: low|medium|high",
    "3. Foco agora: scattered|normal|deep",
    "4. Urgência agora: low|medium|high",
    "5. Carga cognitiva agora: light|moderate|heavy",
    "6. Preferência de resposta agora: summary|balanced|detailed",
    "7. Projeto ativo (opcional)",
    "8. Fadiga agora? yes|no",
    "9. Dor agora? yes|no",
    "10. Sobrecarga visual agora? yes|no",
    "11. Precisa de pausa agora? yes|no",
    "12. Observações do momento (opcional)",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _users_root(root: Path) -> Path:
    return root / "01_Archivus" / "users"


def sci_profiles_dir(root: Path) -> Path:
    return _users_root(root) / "sci_profiles"


def hcb_states_dir(root: Path) -> Path:
    return _users_root(root) / "hcb_states"


def runtime_identity_file(root: Path) -> Path:
    return root / "00_Core" / "config" / "hcb_identity_runtime.json"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_bool(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "y", "yes", "s", "sim", "true"}


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


def run_sci_onboarding_wizard(root: Path, user_id: str, answers: dict | None = None) -> Path:
    answers = answers or {}

    def ask(key: str, prompt: str, default: str = "") -> str:
        if key in answers:
            return str(answers[key])
        suffix = f" [{default}]" if default else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        return raw or default

    display_name = ask("display_name", "Nome de exibição")
    primary_language = ask("primary_language", "Idioma principal", "pt-BR")
    timezone_name = ask("timezone_name", "Fuso horário", "Europe/London")
    role_profile = ask("role_profile", "Perfil principal de uso", "general")
    technical_level = ask("technical_level", "Nível técnico", "intermediate")
    preferred_tone = ask("preferred_tone", "Tom preferido", "balanced")
    response_depth = ask("response_depth", "Profundidade de resposta", "balanced")
    step_by_step = _to_bool(ask("step_by_step", "Precisa de passo a passo? yes/no", "yes"))
    correction_style = ask("correction_style", "Estilo de correção", "mixed")
    needs_adaptation = _to_bool(ask("needs_adaptation", "Precisa de adaptação? yes/no", "no"))
    visual_support = _to_bool(ask("visual_support", "Suporte visual? yes/no", "no"))
    motor_support = _to_bool(ask("motor_support", "Suporte motor? yes/no", "no"))
    fatigue_support = _to_bool(ask("fatigue_support", "Suporte para fadiga? yes/no", "no"))
    accessibility_notes = ask("accessibility_notes", "Observações de acessibilidade", "")

    return create_sci_profile(
        root=root,
        user_id=user_id,
        display_name=display_name,
        primary_language=primary_language,
        timezone_name=timezone_name,
        role_profile=role_profile,
        technical_level=technical_level,
        preferred_tone=preferred_tone,
        response_depth=response_depth,
        step_by_step=step_by_step,
        correction_style=correction_style,
        needs_adaptation=needs_adaptation,
        visual_support=visual_support,
        motor_support=motor_support,
        fatigue_support=fatigue_support,
        accessibility_notes=accessibility_notes,
    )


def run_hcb_state_wizard(root: Path, user_id: str, answers: dict | None = None) -> Path:
    answers = answers or {}

    def ask(key: str, prompt: str, default: str = "") -> str:
        if key in answers:
            return str(answers[key])
        suffix = f" [{default}]" if default else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        return raw or default

    mode = ask("mode", "Modo atual", "work")
    energy = ask("energy", "Energia agora", "medium")
    focus = ask("focus", "Foco agora", "normal")
    urgency = ask("urgency", "Urgência agora", "medium")
    cognitive_load = ask("cognitive_load", "Carga cognitiva agora", "moderate")
    response_preference = ask("response_preference", "Preferência de resposta agora", "balanced")
    active_project = ask("active_project", "Projeto ativo", "")
    fatigue_now = _to_bool(ask("fatigue_now", "Fadiga agora? yes/no", "no"))
    pain_now = _to_bool(ask("pain_now", "Dor agora? yes/no", "no"))
    visual_overload = _to_bool(ask("visual_overload", "Sobrecarga visual agora? yes/no", "no"))
    needs_pause = _to_bool(ask("needs_pause", "Precisa de pausa agora? yes/no", "no"))
    notes = ask("notes", "Observações do momento", "")

    return create_hcb_state(
        root=root,
        user_id=user_id,
        mode=mode,
        energy=energy,
        focus=focus,
        urgency=urgency,
        cognitive_load=cognitive_load,
        response_preference=response_preference,
        active_project=active_project,
        notes=notes,
        fatigue_now=fatigue_now,
        pain_now=pain_now,
        visual_overload=visual_overload,
        needs_pause=needs_pause,
    )


def activate_identity(root: Path, user_id: str) -> Path:
    profile_path = sci_profiles_dir(root) / f"{user_id}.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"SCI profile not found for user_id: {user_id}")
    payload = {
        "active_user_id": user_id,
        "sci_profile_path": str(profile_path),
        "activated_at": _utc_now(),
        "installation_ready": True,
    }
    out = runtime_identity_file(root)
    _write_json(out, payload)
    return out


def get_active_identity(root: Path) -> dict | None:
    path = runtime_identity_file(root)
    if not path.exists():
        return None
    return _read_json(path)


def has_active_identity(root: Path) -> bool:
    payload = get_active_identity(root)
    if not payload:
        return False
    profile_path = payload.get("sci_profile_path", "")
    return bool(profile_path) and Path(profile_path).exists()
