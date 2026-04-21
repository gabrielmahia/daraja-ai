"""
llm_router.py — Shared LLM utility for East African civic apps.
Pattern from Jumuiya (jumuia.streamlit.app) — direct REST, no SDK.

Priority:
  1. GEMINI_API_KEY env var → gemini-1.5-flash (free tier, generous quota)
  2. ANTHROPIC_API_KEY env var → claude-haiku-4-5-20251001
  3. User-supplied key (detected from prefix)
  4. Graceful error with user-friendly message

No external dependencies beyond stdlib urllib.
"""
import os
import json
import urllib.request
import urllib.error

GEMINI_MODELS = [
    ("gemini-1.5-flash",    "v1beta"),
    ("gemini-2.0-flash",    "v1beta"),
    ("gemini-1.5-flash-8b", "v1beta"),
]

_ERRORS = {
    "quota":      "The AI assistant has reached its daily limit — try again later.",
    "no_key":     "No AI key configured. Add a Gemini or Anthropic key to continue.",
    "auth":       "AI key not recognised. Please check it and try again.",
    "unavailable":"AI assistant unavailable right now. Please try again shortly.",
}


def _call_gemini(prompt: str, api_key: str, system: str = "") -> str:
    """Direct REST call to Gemini — no SDK needed."""
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    for model, version in GEMINI_MODELS:
        url = (f"https://generativelanguage.googleapis.com"
               f"/{version}/models/{model}:generateContent?key={api_key}")
        body = json.dumps({
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"maxOutputTokens": 800, "temperature": 0.3},
        }).encode()
        req = urllib.request.Request(url, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RuntimeError(_ERRORS["quota"])
            if e.code in (400, 401, 403):
                raise RuntimeError(_ERRORS["auth"])
            continue  # try next model
        except Exception:
            continue
    raise RuntimeError(_ERRORS["unavailable"])


def _call_anthropic(prompt: str, api_key: str, system: str = "") -> str:
    """Direct REST call to Anthropic claude-haiku — no SDK needed."""
    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 800,
        "system": system or "You are a helpful assistant for Kenya.",
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise RuntimeError(_ERRORS["quota"])
        if e.code in (400, 401, 403):
            raise RuntimeError(_ERRORS["auth"])
        raise RuntimeError(_ERRORS["unavailable"])


def ask(prompt: str, system: str = "", user_key: str = "") -> str:
    """
    Call LLM with automatic provider selection.
    Priority: GEMINI_API_KEY env → ANTHROPIC_API_KEY env → user_key (auto-detected).
    Returns text response or raises RuntimeError with user-friendly message.
    """
    gemini_key    = os.getenv("GEMINI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    # Detect user-supplied key type
    if user_key:
        if user_key.startswith("sk-ant-"):
            anthropic_key = user_key
        elif len(user_key) > 20:  # Gemini keys are long alphanumeric strings
            gemini_key = user_key

    if gemini_key:
        return _call_gemini(prompt, gemini_key, system)
    if anthropic_key:
        return _call_anthropic(prompt, anthropic_key, system)

    raise RuntimeError(_ERRORS["no_key"])


def available_provider(user_key: str = "") -> str:
    """Returns which provider will be used, for UI display."""
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if user_key.startswith("sk-ant-"):
        return "anthropic"
    if len(user_key) > 20:
        return "gemini"
    return "none"
