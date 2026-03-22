#!/usr/bin/env python3
"""
Test Cosmos (vLLM OpenAI API) with a single image file.

Optionally starts vLLM via ``cosmos_launcher_api.py`` (POST /vllm/start), then waits
until the model server answers, then sends one vision request.

  # vLLM already running on :8000:
  python3 test_cosmos_sample_image.py --image sample_frame.jpg

  # Start vLLM through the launcher on :9091 first (can take many minutes):
  python3 test_cosmos_sample_image.py --image sample_frame.jpg --start-vllm

Requires: requests, and a running vLLM serving nvidia/Cosmos-Reason2-2B (or --model).
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import sys
import time
from pathlib import Path

import requests

from vlm_backends import describe_openai_vision


def wait_vllm_ready(vllm_base: str, timeout_s: float = 2400.0, interval_s: float = 5.0) -> None:
    """Poll OpenAI-compatible GET /v1/models until OK or timeout."""
    b = vllm_base.rstrip("/")
    if not b.endswith("/v1"):
        b = b + "/v1"
    url = b + "/models"
    deadline = time.monotonic() + timeout_s
    print(f"Waiting for vLLM at {url} …", file=sys.stderr)
    while time.monotonic() < deadline:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                print("vLLM is up.", file=sys.stderr)
                return
        except requests.RequestException:
            pass
        time.sleep(interval_s)
    print("Timeout waiting for vLLM. Check logs (e.g. COSMOS_VLLM_LOG).", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    here = _SCRIPT_DIR
    p = argparse.ArgumentParser(description="Test Cosmos vLLM with one image")
    p.add_argument(
        "--image",
        type=Path,
        default=here / "sample_frame.jpg",
        help="Path to JPEG/PNG (default: ./sample_frame.jpg next to this script)",
    )
    p.add_argument(
        "--vllm-base",
        default="http://127.0.0.1:8000/v1",
        help="vLLM OpenAI base URL (default: http://127.0.0.1:8000/v1)",
    )
    p.add_argument(
        "--model",
        default="nvidia/Cosmos-Reason2-2B",
        help="Model id served by vLLM",
    )
    p.add_argument(
        "--prompt",
        default="Describe this image in detail.",
        help="User prompt",
    )
    p.add_argument(
        "--launcher",
        default="http://127.0.0.1:9091",
        help="cosmos_launcher_api.py base URL (used with --start-vllm)",
    )
    p.add_argument(
        "--start-vllm",
        action="store_true",
        help="POST {launcher}/vllm/start then wait for vLLM",
    )
    p.add_argument(
        "--wait-timeout",
        type=float,
        default=2400.0,
        help="Max seconds to wait for vLLM after --start-vllm (default: 2400)",
    )
    args = p.parse_args()

    img_path = args.image.resolve()
    if not img_path.is_file():
        print(f"Image not found: {img_path}", file=sys.stderr)
        return 1

    if args.start_vllm:
        lu = args.launcher.rstrip("/")
        print(f"POST {lu}/vllm/start …", file=sys.stderr)
        try:
            r = requests.post(f"{lu}/vllm/start", timeout=30)
            print(r.text, file=sys.stderr)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Launcher request failed: {e}", file=sys.stderr)
            return 1
        wait_vllm_ready(args.vllm_base, timeout_s=args.wait_timeout)

    raw = img_path.read_bytes()
    mime = mimetypes.guess_type(str(img_path))[0] or "image/jpeg"
    b64 = base64.b64encode(raw).decode("ascii")

    print(f"Sending {img_path} ({mime}) to {args.vllm_base} model={args.model} …", file=sys.stderr)
    t0 = time.perf_counter()
    try:
        text = describe_openai_vision(
            b64,
            base_url=args.vllm_base,
            model=args.model,
            prompt=args.prompt,
            mime=mime if mime.startswith("image/") else "image/jpeg",
            timeout=(30.0, 900.0),
        )
    except requests.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        if e.response is not None:
            print(e.response.text[:4000], file=sys.stderr)
        return 1
    except requests.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        err = str(e).lower()
        if "connection refused" in err or "failed to establish" in err:
            print(
                "\nNothing is listening on the vLLM port (default :8000). Start the server first:\n"
                "  • Manual:  cd ~/cosmos-reason2 && uv run vllm serve nvidia/Cosmos-Reason2-2B ... --port 8000\n"
                "  • Launcher: run cosmos_launcher_api.py then:\n"
                "      curl -s -X POST http://127.0.0.1:9091/vllm/start\n"
                "  • Or:      python3 test_cosmos_sample_image.py --image ... --start-vllm\n"
                "Wait until logs show 'Application startup complete.' then retry.",
                file=sys.stderr,
            )
        return 1
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    dt = time.perf_counter() - t0
    print(f"\n--- ({dt:.1f}s) ---\n{text}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
