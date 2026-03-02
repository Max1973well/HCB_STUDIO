from datetime import datetime


def build_plan(goal: str) -> dict:
    text = (goal or "").strip().lower()
    steps = []

    if any(k in text for k in ("status", "saude", "diagnostico")):
        steps.append({"step": "Diagnosticar estado do sistema", "command_args": ["status"]})
    if any(k in text for k in ("checkpoint", "guardanapo", "contexto")):
        steps.append({"step": "Ler contexto de checkpoints", "command_args": ["napkin"]})
    if any(k in text for k in ("organizar", "triagem", "quarentena")):
        steps.append({"step": "Executar triagem inteligente", "command_args": ["triage", "--mode", "smart"]})
    if any(k in text for k in ("ia", "gemini", "motor")):
        steps.append({"step": "Verificar motor de IA", "command_args": ["ai", "status"]})

    if not steps:
        steps = [
            {"step": "Diagnosticar estado base", "command_args": ["status"]},
            {"step": "Verificar motor de IA", "command_args": ["ai", "status"]},
        ]

    return {
        "goal": goal,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "steps": steps,
    }
