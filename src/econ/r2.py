"""Cloudflare R2 upload via wrangler CLI.

Auth: reads CLOUDFLARE_API_TOKEN from env (wrangler picks it up automatically).
The runner needs Node available (preinstalled on ubuntu-latest); wrangler is
fetched on-demand by `npx`.
"""
import os
import subprocess
from pathlib import Path


def upload(local_path: Path, key: str, content_type: str = "application/pdf") -> str:
    bucket = os.environ.get("R2_BUCKET", "economist-reader")
    cmd = [
        "npx",
        "--yes",
        "wrangler",
        "r2",
        "object",
        "put",
        f"{bucket}/{key}",
        "--file", str(local_path),
        "--content-type", content_type,
        "--remote",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(
            f"wrangler upload failed (rc={result.returncode}):\n"
            f"STDOUT: {result.stdout[-500:]}\nSTDERR: {result.stderr[-500:]}"
        )
    return key
