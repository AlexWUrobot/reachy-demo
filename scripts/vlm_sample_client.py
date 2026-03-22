#!/usr/bin/env python3
"""Send a sample image to the HTTP VLM server (same contract as cooking_vision.py).

POST JSON: {"image_b64": "<jpeg base64>", "prompt": "<string>"}

Usage:
  export VLM_SERVER_URL=http://127.0.0.1:8000/describe
  python3 scripts/vlm_sample_client.py path/to/image.jpg

  python3 scripts/vlm_sample_client.py --url http://host:port/endpoint image.png \\
      --prompt "What do you see?"
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError as e:
    print("Install requests: pip install requests", file=sys.stderr)
    raise SystemExit(1) from e


def image_to_jpeg_b64(path: Path) -> str:
    """Read image file; encode as JPEG bytes then base64 (uses OpenCV if available)."""
    suffix = path.suffix.lower()
    raw = path.read_bytes()

    if suffix in (".jpg", ".jpeg"):
        return base64.b64encode(raw).decode("utf-8")

    try:
        import cv2
        import numpy as np
    except ImportError:
        print(
            "Non-JPEG images need opencv-python: pip install opencv-python",
            file=sys.stderr,
        )
        raise SystemExit(1)

    arr = np.frombuffer(raw, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        print(f"Could not decode image: {path}", file=sys.stderr)
        raise SystemExit(1)
    ok, buf = cv2.imencode(".jpg", bgr)
    if not ok:
        print("Failed to encode as JPEG", file=sys.stderr)
        raise SystemExit(1)
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def parse_description(payload: object) -> str:
    if isinstance(payload, dict):
        for key in ("description", "text", "result", "message", "caption"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    return json.dumps(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="POST a sample image to the VLM server.")
    parser.add_argument(
        "image",
        type=Path,
        help="Path to an image file (jpg/png/webp/etc.)",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("VLM_SERVER_URL", ""),
        help="VLM endpoint URL (default: env VLM_SERVER_URL)",
    )
    parser.add_argument(
        "--prompt",
        default="Briefly describe this image.",
        help="Prompt for the vision model",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("VLM_REQUEST_TIMEOUT", "10")),
        help="HTTP timeout in seconds",
    )
    args = parser.parse_args()

    if not args.url:
        print(
            "Set --url or environment variable VLM_SERVER_URL",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if not args.image.is_file():
        print(f"Not a file: {args.image}", file=sys.stderr)
        raise SystemExit(1)

    image_b64 = image_to_jpeg_b64(args.image)
    body = {"image_b64": image_b64, "prompt": args.prompt}

    print(f"POST {args.url}", file=sys.stderr)
    resp = requests.post(args.url, json=body, timeout=args.timeout)
    print(f"HTTP {resp.status_code}", file=sys.stderr)

    if resp.status_code >= 400:
        print(resp.text, file=sys.stderr)
        raise SystemExit(1)

    try:
        data = resp.json()
    except Exception:
        print(resp.text)
        return

    print(parse_description(data))


if __name__ == "__main__":
    main()
