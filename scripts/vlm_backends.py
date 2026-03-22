"""Helpers for OpenAI-compatible vision APIs (vLLM, etc.)."""

from __future__ import annotations

import json
from typing import Any, Tuple, Union

import requests


def describe_openai_vision(
    image_b64: str,
    *,
    base_url: str,
    model: str,
    prompt: str,
    mime: str = "image/jpeg",
    timeout: Union[float, Tuple[float, float]] = (30.0, 900.0),
) -> str:
    """Send one image + text to ``POST {base}/chat/completions`` (OpenAI multimodal format).

    ``base_url`` should be like ``http://127.0.0.1:8000/v1`` (with or without trailing slash).
    """
    b = base_url.rstrip("/")
    url = f"{b}/chat/completions"

    data_url = f"data:{mime};base64,{image_b64}"
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                ],
            }
        ],
        "max_tokens": 1024,
    }

    r = requests.post(url, json=body, timeout=timeout)
    r.raise_for_status()
    payload = r.json()

    try:
        choice = payload["choices"][0]
        msg = choice.get("message") or {}
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            # Some APIs return list of parts
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))
            if parts:
                return "\n".join(parts).strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Unexpected chat/completions response: {json.dumps(payload)[:2000]}") from e

    raise RuntimeError(f"No text content in response: {json.dumps(payload)[:2000]}")
