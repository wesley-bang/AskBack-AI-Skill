#!/usr/bin/env python3
"""Render storyboard scenes and narration into one MP4."""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys


DISCLAIMER = "AI 生成教學示範，非原講者本人"


def command(args):
    return subprocess.run(args, check=True, text=True, capture_output=True)


def get_duration(path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    result = command([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)])
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def font_path():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if pathlib.Path(candidate).exists():
            return candidate
    return None


def render_slide(scene, output, workdir, storyboard_dir, width=1280, height=720):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("Pillow is required; run python3 -m pip install -r requirements.txt") from exc

    asset = scene.get("asset")
    asset_path = None
    if asset:
        candidate = pathlib.Path(asset)
        candidates = [candidate]
        if not candidate.is_absolute():
            candidates.extend([workdir / candidate, storyboard_dir / candidate])
        asset_path = next((item for item in candidates if item.exists()), None)
    if asset_path:
        image = Image.open(asset_path).convert("RGB").resize((width, height))
    else:
        image = Image.new("RGB", (width, height), (247, 249, 252))
    draw = ImageDraw.Draw(image)
    font = font_path()
    if not font:
        raise SystemExit("No usable font found. Install Noto Sans CJK or provide a system font.")
    title_font = ImageFont.truetype(font, 42)
    body_font = ImageFont.truetype(font, 30)
    small_font = ImageFont.truetype(font, 20)

    # A translucent card keeps generated illustrations useful while guaranteeing readable text.
    draw.rounded_rectangle((56, 42, width - 56, height - 78), radius=24, fill=(255, 255, 255, 232), outline=(44, 62, 80), width=2)
    draw.text((92, 74), scene.get("title", "補充教學"), fill=(24, 53, 82), font=title_font)
    body = scene.get("body", [])
    if isinstance(body, str):
        body = [body]
    y = 150
    for line in body:
        # Simple wrapping keeps long Chinese lines within the card.
        words = list(line)
        chunk = ""
        chunks = []
        for char in words:
            if len(chunk) >= 25:
                chunks.append(chunk)
                chunk = ""
            chunk += char
        if chunk:
            chunks.append(chunk)
        for item in chunks:
            draw.text((100, y), item, fill=(34, 39, 46), font=body_font)
            y += 48
        y += 14

    draw.rectangle((0, height - 42, width, height), fill=(24, 53, 82))
    draw.text((28, height - 34), DISCLAIMER, fill=(255, 255, 255), font=small_font)
    image.save(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--storyboard", required=True)
    parser.add_argument("--workdir", default="work")
    parser.add_argument("--output", default="outputs/askback.mp4")
    parser.add_argument("--allow-silent", action="store_true", help="development fallback only; do not use for submission")
    args = parser.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required")
    storyboard_path = pathlib.Path(args.storyboard)
    workdir = pathlib.Path(args.workdir)
    data = json.loads(storyboard_path.read_text(encoding="utf-8"))
    scenes = data.get("scenes", [])
    if not scenes:
        raise SystemExit("storyboard has no scenes")
    if data.get("language") != "zh-TW":
        raise SystemExit("storyboard language must be zh-TW")

    assets_dir = workdir / "rendered_slides"
    segments_dir = workdir / "segments"
    assets_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    concat_file = workdir / "concat.txt"
    segment_paths = []

    for index, scene in enumerate(scenes, 1):
        slide = assets_dir / f"scene_{index:02d}.png"
        render_slide(scene, slide, workdir, storyboard_path.parent)
        audio = scene.get("audio")
        if audio:
            audio_path = pathlib.Path(audio)
            if not audio_path.is_absolute() and not audio_path.exists():
                for candidate in (workdir / audio_path, storyboard_path.parent / audio_path):
                    if candidate.exists():
                        audio_path = candidate
                        break
        else:
            audio_path = workdir / "audio" / f"scene_{index:02d}.wav"
        segment = segments_dir / f"scene_{index:02d}.mp4"
        duration = get_duration(audio_path) if audio_path.exists() else None
        if duration is None:
            if not args.allow_silent:
                raise SystemExit(f"missing narration audio for {scene.get('id', index)}: {audio_path}")
            duration = float(scene.get("duration", 3))
            command([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(slide),
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(segment)
            ])
        else:
            command([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(slide),
                "-i", str(audio_path), "-t", str(duration), "-c:v", "libx264", "-preset", "medium",
                "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-ar", "48000", "-b:a", "128k",
                "-shortest", str(segment)
            ])
        segment_paths.append(segment)

    concat_file.write_text("\n".join(f"file '{p.resolve()}'" for p in segment_paths) + "\n", encoding="utf-8")
    command([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", str(output)
    ])
    print(json.dumps({"output": str(output), "duration_seconds": get_duration(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
