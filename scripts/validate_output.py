#!/usr/bin/env python3
"""Validate the deliverable's basic assignment constraints."""

import argparse
import json
import pathlib
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    args = parser.parse_args()
    path = pathlib.Path(args.video)
    if not path.exists():
        raise SystemExit(f"missing output: {path}")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise SystemExit("ffprobe is required")
    result = subprocess.run([
        ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ], check=True, text=True, capture_output=True)
    info = json.loads(result.stdout)
    duration = float(info.get("format", {}).get("duration", 0))
    streams = info.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    errors = []
    if not 30 <= duration <= 90:
        errors.append(f"duration {duration:.2f}s is outside 30–90s")
    if not has_video:
        errors.append("no video stream")
    if not has_audio:
        errors.append("no audio stream")
    if errors:
        raise SystemExit("output validation failed: " + "; ".join(errors))
    print(json.dumps({"ok": True, "duration_seconds": duration, "has_video": has_video, "has_audio": has_audio}, ensure_ascii=False))


if __name__ == "__main__":
    main()

