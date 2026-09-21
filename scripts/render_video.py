#!/usr/bin/env python3
"""Render storyboard scenes and narration into one MP4."""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import os


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
    configured = os.environ.get("ASKBACK_FONT_PATH")
    if configured and pathlib.Path(configured).exists():
        return configured
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


def draw_arrow(draw, start, end, fill=(210, 70, 56), width=6):
    import math
    draw.line((start[0], start[1], end[0], end[1]), fill=fill, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = 18
    points = [
        end,
        (end[0] - size * math.cos(angle - 0.5), end[1] - size * math.sin(angle - 0.5)),
        (end[0] - size * math.cos(angle + 0.5), end[1] - size * math.sin(angle + 0.5)),
    ]
    draw.polygon(points, fill=fill)


def draw_tube(draw, x, top, width, height, mercury_height, font, label):
    outline = (48, 55, 65)
    mercury = (188, 192, 198)
    draw.rounded_rectangle((x, top, x + width, top + height), radius=width // 2,
                           outline=outline, width=4, fill=(242, 231, 214))
    bottom = top + height - 8
    mercury_top = bottom - mercury_height
    draw.rectangle((x + 5, mercury_top, x + width - 5, bottom), fill=mercury)
    draw.line((x + 5, mercury_top, x + width - 5, mercury_top), fill=outline, width=3)
    draw.text((x + width // 2 - 26, bottom + 14), label, fill=outline, font=font)


def draw_diagram(draw, scene, font, small_font, width=1280, height=720):
    """Draw exact symbols and comparisons instead of asking an image model to typeset them."""
    diagram = scene.get("diagram")
    if not diagram:
        return
    ink = (45, 54, 65)
    red = (211, 75, 61)
    blue = (48, 110, 160)
    x0, y0 = 735, 182
    if diagram == "tube_compare":
        draw_tube(draw, x0, y0, 72, 300, 155, small_font, "細管")
        draw_tube(draw, x0 + 190, y0, 125, 300, 155, small_font, "粗管")
        draw.line((x0 - 18, y0 + 145, x0 + 330, y0 + 145), fill=red, width=3)
        draw.text((x0 + 80, y0 + 100), "76 cm", fill=red, font=small_font)
        draw.text((x0 + 57, y0 - 45), "高度相同", fill=ink, font=font)
    elif diagram == "force_area":
        draw_tube(draw, x0, y0 + 30, 70, 260, 120, small_font, "小 A")
        draw_tube(draw, x0 + 210, y0, 130, 290, 145, small_font, "大 A")
        draw_arrow(draw, (x0 + 35, y0 + 125), (x0 + 35, y0 + 245), blue)
        draw_arrow(draw, (x0 + 275, y0 + 105), (x0 + 275, y0 + 255), blue, 8)
        draw.text((x0 + 12, y0 + 305), "F", fill=blue, font=font)
        draw.text((x0 + 252, y0 + 305), "2F", fill=blue, font=font)
        draw.text((x0 + 74, y0 + 365), "A  →  2A", fill=red, font=font)
    elif diagram == "pressure_formula":
        draw.rounded_rectangle((x0 - 15, y0 + 15, x0 + 425, y0 + 125), radius=18,
                               fill=(255, 245, 224), outline=ink, width=3)
        draw.text((x0 + 35, y0 + 42), "P = F / A", fill=ink, font=font)
        draw.text((x0 + 22, y0 + 180), "2F / 2A = F / A", fill=red, font=font)
        draw.text((x0 + 30, y0 + 300), "壓力不變", fill=blue, font=font)
    elif diagram == "tube_long":
        draw_tube(draw, x0, y0 + 65, 72, 230, 120, small_font, "短管")
        draw_tube(draw, x0 + 195, y0, 72, 295, 120, small_font, "長管")
        draw.line((x0 - 15, y0 + 175, x0 + 280, y0 + 175), fill=red, width=3)
        draw.text((x0 + 80, y0 + 125), "76 cm", fill=red, font=small_font)
        draw.text((x0 + 100, y0 - 38), "上方是真空", fill=ink, font=small_font)
    elif diagram == "summary":
        draw.rounded_rectangle((x0, y0 + 20, x0 + 360, y0 + 110), radius=18,
                               fill=(222, 239, 249), outline=blue, width=3)
        draw.text((x0 + 42, y0 + 48), "大氣壓力", fill=blue, font=font)
        draw_arrow(draw, (x0 + 180, y0 + 155), (x0 + 180, y0 + 235), red)
        draw.rounded_rectangle((x0, y0 + 270, x0 + 360, y0 + 360), radius=18,
                               fill=(255, 239, 218), outline=red, width=3)
        draw.text((x0 + 42, y0 + 298), "76 cm 汞柱", fill=red, font=font)


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
        image = Image.new("RGB", (width, height), (223, 198, 166))
    draw = ImageDraw.Draw(image)
    font = font_path()
    if not font:
        raise SystemExit("No usable font found. Install Noto Sans CJK or provide a system font.")
    title_font = ImageFont.truetype(font, 42)
    body_font = ImageFont.truetype(font, 30)
    small_font = ImageFont.truetype(font, 20)

    # A translucent card keeps generated illustrations useful while guaranteeing readable text.
    draw.rounded_rectangle((56, 42, width - 56, height - 78), radius=24, fill=(255, 252, 246), outline=(44, 62, 80), width=2)
    draw.text((92, 74), scene.get("title", "補充教學"), fill=(24, 53, 82), font=title_font)
    draw_diagram(draw, scene, body_font, small_font, width, height)
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
            if len(chunk) >= 17:
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
            audio_path = None
            for extension in ("wav", "mp3", "m4a", "flac", "ogg"):
                candidate = workdir / "audio" / f"scene_{index:02d}.{extension}"
                if candidate.exists():
                    audio_path = candidate
                    break
            if audio_path is None:
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
