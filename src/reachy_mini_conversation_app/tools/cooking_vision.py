"""Cooking-scene vision: sample Reachy camera at a steady rate and describe frames."""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any, Dict, List

import cv2
import requests

from reachy_mini_conversation_app.config import config
from reachy_mini_conversation_app.tools.core_tools import Tool, ToolDependencies


logger = logging.getLogger(__name__)

_DEFAULT_PROMPT = (
    "Briefly describe the cooking scene: ingredients, cookware, stove or counter, "
    "and what the person appears to be doing."
)


def _jpeg_b64(frame: Any) -> str:
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise RuntimeError("Failed to encode frame as JPEG")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _jpeg_bytes(frame: Any) -> bytes:
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise RuntimeError("Failed to encode frame as JPEG")
    return buf.tobytes()


def _parse_vlm_http_response(resp: requests.Response) -> str:
    try:
        data = resp.json()
        if isinstance(data, dict):
            for key in ("description", "text", "result", "message", "caption"):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        if isinstance(data, str) and data.strip():
            return data.strip()
    except Exception:
        pass
    text = (resp.text or "").strip()
    return text if text else "(empty response)"


async def _describe_frame(
    frame: Any,
    deps: ToolDependencies,
    prompt: str,
) -> str:
    if deps.vision_manager is not None:
        vision_result = await asyncio.to_thread(
            deps.vision_manager.processor.process_image,
            frame,
            prompt,
        )
        if isinstance(vision_result, dict) and "error" in vision_result:
            return str(vision_result["error"])
        if isinstance(vision_result, str):
            return vision_result
        return str(vision_result)

    vlm_url = config.VLM_SERVER_URL
    if not vlm_url:
        return (
            "No vision backend: set VLM_SERVER_URL for an HTTP VLM, "
            "or run the app with --local-vision for a local model."
        )

    timeout = config.VLM_REQUEST_TIMEOUT
    fmt = getattr(config, "VLM_REQUEST_FORMAT", "multipart") or "multipart"
    if fmt not in ("json", "multipart"):
        fmt = "multipart"

    def _post() -> requests.Response:
        if fmt == "json":
            b64 = _jpeg_b64(frame)
            return requests.post(
                vlm_url,
                json={"image_b64": b64, "prompt": prompt},
                timeout=timeout,
            )
        jpeg = _jpeg_bytes(frame)
        return requests.post(
            vlm_url,
            files={"image": ("frame.jpg", jpeg, "image/jpeg")},
            data={"prompt": prompt},
            timeout=timeout,
        )

    resp = await asyncio.to_thread(_post)
    if resp.status_code >= 400:
        return f"VLM HTTP {resp.status_code}: {resp.text[:500]}"
    return _parse_vlm_http_response(resp)


class CookingVision(Tool):
    """Periodic camera sampling + VLM descriptions while cooking."""

    name = "start_cooking_vision"
    description = (
        "ONLY use when the user explicitly starts cooking vision monitoring—typically they say "
        "\"start cooking\" or a clear equivalent (e.g. \"begin cooking camera\", \"start the cooking view\"). "
        "Do NOT call this for general cooking chat, recipes, grocery cart, or vague mentions of cooking. "
        "For a single snapshot or one-off vision question, use the `camera` tool instead. "
        "When called: samples the camera at a steady rate (default 1 Hz), sends frames to the vision backend, "
        "and returns timed descriptions."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "sample_rate_hz": {
                "type": "number",
                "description": "How many frames per second to capture and describe (default 1.0, max 5).",
            },
            "duration_seconds": {
                "type": "number",
                "description": "How long to keep sampling in seconds (default 5, max 120).",
            },
            "prompt": {
                "type": "string",
                "description": "Optional question or focus for the vision model (e.g. 'what is on the cutting board?').",
            },
        },
        "required": [],
    }

    async def __call__(self, deps: ToolDependencies, **kwargs: Any) -> Dict[str, Any]:
        sample_rate_hz = float(kwargs.get("sample_rate_hz") or 1.0)
        duration_seconds = float(kwargs.get("duration_seconds") or 10.0)
        prompt = (kwargs.get("prompt") or "").strip() or _DEFAULT_PROMPT

        sample_rate_hz = max(0.1, min(sample_rate_hz, 5.0))
        duration_seconds = max(0.5, min(duration_seconds, 120.0))

        if deps.camera_worker is None:
            return {"status": "error", "message": "Camera worker not available (use camera-enabled run)."}

        # Avoid racing the camera thread before the first successful get_frame() fills latest_frame.
        first = await _wait_for_frame(deps.camera_worker, timeout_s=5.0)
        if first is None:
            logger.error(
                "cooking_vision: no frame after 5s — check reachy-mini-daemon, physical camera, "
                "and run without --no-camera. CameraWorker only sets latest_frame when "
                "reachy_mini.media.get_frame() returns non-None.",
            )
            return {
                "status": "error",
                "message": (
                    "No camera frame available. Ensure the daemon is running, camera works, "
                    "and the app was not started with --no-camera."
                ),
            }

        interval = 1.0 / sample_rate_hz
        deadline = time.monotonic() + duration_seconds
        samples: List[Dict[str, Any]] = []
        t0 = time.monotonic()

        while time.monotonic() < deadline:
            frame = deps.camera_worker.get_latest_frame()
            if frame is None:
                samples.append(
                    {
                        "t_seconds": round(time.monotonic() - t0, 2),
                        "error": "No frame available",
                    },
                )
            else:
                logger.debug("cooking_vision frame shape=%s", getattr(frame, "shape", None))
                desc = await _describe_frame(frame, deps, prompt)
                samples.append(
                    {
                        "t_seconds": round(time.monotonic() - t0, 2),
                        "description": desc,
                    },
                )

            await asyncio.sleep(interval)

        summaries = [
            s["description"]
            for s in samples
            if isinstance(s.get("description"), str) and s["description"]
        ]
        summary = " | ".join(summaries[:3]) if summaries else ""

        return {
            "status": "success",
            "sample_rate_hz": sample_rate_hz,
            "duration_seconds": duration_seconds,
            "prompt": prompt,
            "samples": samples,
            "summary": summary,
        }
