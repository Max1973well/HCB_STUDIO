import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


DEFAULT_CONFIG = {
    "active_provider": "gemini",
    "providers": {
        "gemini": {
            "enabled": True,
            "model": "gemini-1.5-flash",
            "api_key_env": "GEMINI_API_KEY",
            "temperature": 0.2,
        },
        "ollama": {
            "enabled": True,
            "model": "dolphin2.2-mistral",
            "endpoint": "http://127.0.0.1:11434/api/generate",
            "temperature": 0.2,
        }
    },
}


def load_engine_config(config_path: Path) -> dict:
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_engine_config(config_path: Path, config: dict) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def set_active_provider(config_path: Path, provider: str, model: str | None = None) -> dict:
    config = load_engine_config(config_path)
    if provider not in config.get("providers", {}):
        raise ValueError(f"Provider '{provider}' is not configured.")
    config["active_provider"] = provider
    if model:
        config["providers"][provider]["model"] = model
    save_engine_config(config_path, config)
    return config


def _gemini_generate(prompt: str, provider_cfg: dict, system_prompt: str = "") -> dict:
    env_var = provider_cfg.get("api_key_env", "GEMINI_API_KEY")
    api_key = os.getenv(env_var, "").strip()
    if not api_key:
        raise RuntimeError(f"Missing API key in environment variable: {env_var}")

    model = provider_cfg.get("model", "gemini-1.5-flash")
    temperature = provider_cfg.get("temperature", 0.2)

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(api_key)}"
    )
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    
    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [{"text": system_prompt}]
        }
        
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Gemini connection error: {e}") from e

    parsed = json.loads(raw)
    text = ""
    candidates = parsed.get("candidates") or []
    if candidates:
        parts = (((candidates[0] or {}).get("content") or {}).get("parts")) or []
        text = "".join((p or {}).get("text", "") for p in parts).strip()

    return {
        "provider": "gemini",
        "model": model,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "text": text,
        "raw": parsed,
    }


def _ollama_generate(prompt: str, provider_cfg: dict, system_prompt: str = "") -> dict:
    model = provider_cfg.get("model", "dolphin2.2-mistral")
    temperature = provider_cfg.get("temperature", 0.2)
    endpoint = provider_cfg.get("endpoint", "http://127.0.0.1:11434/api/generate")

    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "temperature": temperature,
        "stream": False
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama connection error (Is Ollama running?): {e}") from e

    parsed = json.loads(raw)
    text = parsed.get("response", "").strip()

    return {
        "provider": "ollama",
        "model": model,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "text": text,
        "raw": parsed,
    }

def generate_with_active_provider(config_path: Path, prompt: str, system_prompt: str = "") -> dict:
    config = load_engine_config(config_path)
    active = config.get("active_provider", "gemini")
    providers = config.get("providers", {})
    provider_cfg = providers.get(active)

    if not provider_cfg or not provider_cfg.get("enabled", False):
        raise RuntimeError(f"Active provider '{active}' is not enabled/configured.")

    if active == "gemini":
        return _gemini_generate(prompt, provider_cfg, system_prompt=system_prompt)
    elif active == "ollama":
        return _ollama_generate(prompt, provider_cfg, system_prompt=system_prompt)
        
    raise RuntimeError(f"Provider '{active}' not implemented yet.")
