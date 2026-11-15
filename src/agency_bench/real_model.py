"""Real-model client (OWNER-RULES GATED — read before running).

LLM calls are allowed ONLY through the owner's Z.ai Coding Plan:

    export AGENCY_ZAI_BASE_URL="https://api.z.ai/api/coding/paas/v4"
    export AGENCY_ZAI_MODEL="glm-5.3-flash"      # pinned, no alternatives
    export AGENCY_ZAI_KEY="<key from AGENCY_ZAI_KEY>"

Rules baked into this module:
- model is pinned to glm-5.3-flash; nothing else may be configured;
- flat subscription: on ANY billing/endpoint error we raise BillingError and
  STOP. There is deliberately no pay-per-call fallback provider.
- every entry point is inert without AGENCY_ZAI_KEY (raises
  RealModelNotConfigured) so importing this module is offline-safe.

Uses only urllib (stdlib) — the core stays zero-dependency under PEP 668.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
PINNED_MODEL = "glm-5.3-flash"


class RealModelNotConfigured(RuntimeError):
    """No AGENCY_ZAI_KEY in the environment — real runs are locked."""


class BillingError(RuntimeError):
    """Billing/endpoint error from the Z.ai Coding Plan — STOP per owner rules."""


def resolve_config() -> dict:
    key = os.environ.get("AGENCY_ZAI_KEY")
    base_url = os.environ.get("AGENCY_ZAI_BASE_URL", DEFAULT_BASE_URL)
    model = os.environ.get("AGENCY_ZAI_MODEL", PINNED_MODEL)
    if model != PINNED_MODEL:
        raise RealModelNotConfigured(
            f"model {model!r} rejected: owner rules pin glm-5.3-flash ONLY"
        )
    return {"key": key, "base_url": base_url, "model": model}


def chat(messages: list[dict], max_output_tokens: int = 512) -> dict:
    """One chat completion through the Z.ai Coding Plan (OpenAI-compatible).

    Returns {"content": str, "usage": {...}}. Raises RealModelNotConfigured
    without a key; raises BillingError on billing/endpoint errors (STOP).
    """
    cfg = resolve_config()
    if not cfg["key"]:
        raise RealModelNotConfigured(
            "AGENCY_ZAI_KEY not set — real-model runs are owner-approval-gated. "
            "STOP: do not substitute another provider."
        )
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "max_tokens": max_output_tokens,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        if exc.code in (401, 402, 403, 429):
            raise BillingError(
                f"Z.ai Coding Plan billing/endpoint error (HTTP {exc.code}): {detail} — "
                "STOP per owner rules; never fall back to pay-per-call providers."
            ) from exc
        raise RuntimeError(f"Z.ai request failed (HTTP {exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise BillingError(
            f"Z.ai endpoint unreachable ({exc.reason}) — STOP per owner rules; "
            "do not retry against a different provider."
        ) from exc
    usage = body.get("usage", {})
    content = ""
    if body.get("choices"):
        content = body["choices"][0].get("message", {}).get("content", "")
    return {"content": content, "usage": usage, "model": body.get("model", cfg["model"])}
