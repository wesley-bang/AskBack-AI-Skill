#!/usr/bin/env python3
"""Inspect the causally bounded AskBack input and extract representative frames."""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys


def run_json(command):
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="input")
    parser.add_argument("--work", default="work")
    args = parser.parse_args()
    input_dir = pathlib.Path(args.input)
    work_dir = pathlib.Path(args.work)
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    case_path = input_dir / "case_input.json"
    video_path = input_dir / "prefix.mp4"
    if not case_path.exists():
        raise SystemExit(f"missing {case_path}")
    if not video_path.exists():
        raise SystemExit(f"missing {video_path}")

    case = json.loads(case_path.read_text(encoding="utf-8"))
    if case.get("video_path") not in (None, "prefix.mp4"):
        raise SystemExit("case_input.json must point to the bounded prefix.mp4")
    if float(case.get("allowed_source_end_seconds", 0)) <= 0:
        raise SystemExit("allowed_source_end_seconds must be positive")

    ffprobe = shutil.which("ffprobe")
    ffmpeg = shutil.which("ffmpeg")
    if not ffprobe or not ffmpeg:
        raise SystemExit("ffmpeg and ffprobe are required")

    metadata = run_json([
        ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video_path)
    ])
    duration = float(metadata.get("format", {}).get("duration", 0))
    if duration > float(case["allowed_source_end_seconds"]) + 1.0:
        raise SystemExit("prefix.mp4 is longer than its declared causal boundary")

    # One frame every 5 seconds is enough for an agent to understand the visual rhythm.
    subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_path),
        "-vf", "fps=1/5,scale=640:-2", str(frames_dir / "frame_%03d.jpg")
    ], check=True)

    subtitle_path = input_dir / "prefix.vtt"
    analysis = {
        "case": case,
        "video": {
            "duration_seconds": duration,
            "metadata": metadata,
            "frame_dir": str(frames_dir),
        },
        "subtitle": {
            "present": subtitle_path.exists(),
            "path": str(subtitle_path) if subtitle_path.exists() else None,
        },
    }
    (work_dir / "analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"analysis": str(work_dir / "analysis.json"), "frames": str(frames_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

