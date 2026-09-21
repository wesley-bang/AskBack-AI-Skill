#!/usr/bin/env python3
"""Create a causally bounded storyboard with an OpenAI-compatible model.

The script is intentionally small: the agent still owns the pedagogical
judgement, while this file makes the boring JSON/API plumbing repeatable.
If no API key is present, V08 has a deterministic reference draft so the
repository can be smoke-tested offline. Other cases fail loudly instead of
pretending that a generic explanation is correct.
"""

import argparse
import base64
import json
import os
import pathlib
import re
import urllib.error
import urllib.request


DISCLAIMER = "AI 生成教學示範，非原講者本人"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def bounded_subtitle(input_dir):
    path = input_dir / "prefix.vtt"
    if not path.exists():
        return "（此題沒有字幕；請依據前段影片與 case_input.json 理解。）"
    # This file is supplied as prefix.vtt, but keep the boundary explicit.
    return path.read_text(encoding="utf-8", errors="replace")


def image_data_url(path):
    mime = "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def reference_v08(case):
    return {
        "title": "為什麼玻璃管變粗，水銀高度不變？",
        "language": "zh-TW",
        "style": "動畫角色劇：用提問者與小老師的對話，搭配簡單示意圖",
        "disclaimer": DISCLAIMER,
        "scenes": [
            {
                "id": "scene_01", "duration": 7,
                "title": "先回答問題",
                "body": ["管子變粗，水銀柱高度仍是 76 公分。", "關鍵不是總重量，而是壓力。"],
                "narration": "你的想法只差一個關鍵：大氣壓力不是在撐一個固定重量，而是在同樣面積上產生壓力。玻璃管變粗時，水銀高度仍然是七十六公分。",
                "visual_prompt": "兩個粗細不同的托里切利玻璃管，都標示七十六公分；用簡單角色對話呈現。",
                "diagram": "tube_compare"
            },
            {
                "id": "scene_02", "duration": 8,
                "title": "容易混淆的地方",
                "body": ["粗管：水銀變多，也變重", "但底部受力面積也變大"],
                "narration": "沒錯，粗管裡的水銀總量會增加，所以總重量變大。但是，水銀底部和容器接觸的面積也同時變大。只看重量，會把力和壓力混在一起。",
                "visual_prompt": "左邊顯示較少水銀與小面積，右邊顯示較多水銀與大面積；以箭頭標示重量與受力面積。",
                "diagram": "force_area"
            },
            {
                "id": "scene_03", "duration": 10,
                "title": "用公式看清楚",
                "body": ["壓力 = 力 ÷ 面積", "重量和面積一起放大，壓力不變"],
                "narration": "壓力等於力除以面積。假設管子的截面積變成兩倍，水銀的重量大約也變成兩倍；重量除以面積，比例沒有改變。所以大氣壓力和水銀柱產生的壓力仍然可以平衡。",
                "visual_prompt": "板書式呈現 P 等於 F 除以 A，接著顯示 2F 除以 2A 仍等於 F 除以 A。",
                "diagram": "pressure_formula"
            },
            {
                "id": "scene_04", "duration": 8,
                "title": "那換成更長的管子呢？",
                "body": ["只要水銀夠多，長管不會改變高度", "高度由大氣壓力決定"],
                "narration": "如果只是把玻璃管加長，水銀也不會因此升得更高。只要管子夠長、水銀量足夠，平衡高度由大氣壓力決定，標準狀況下約是七十六公分。",
                "visual_prompt": "同樣粗細的短管與長管並列，兩邊水銀高度都畫在七十六公分，長管上方留真空。",
                "diagram": "tube_long"
            },
            {
                "id": "scene_05", "duration": 8,
                "title": "一句話記住",
                "body": ["粗細、長短是裝置條件", "平衡高度由大氣壓力決定"],
                "narration": "所以要記住：管子變粗，重量和受力面積一起增加，壓力不變；管子變長，只是提供更多空間。托里切利實驗量到的七十六公分，正是大氣壓力決定的平衡高度。",
                "visual_prompt": "角色圈出七十六公分，旁邊出現大氣壓力等於水銀柱壓力的結論，接回原課程。",
                "diagram": "summary"
            }
        ]
    }


def clean_model_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    return json.loads(text)


def request_storyboard(case, subtitles, frame_paths, model):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    system = """你是 AskBack 補充教學影片的教學設計師。只可使用使用者提供的 case、prefix 影片代表畫面與 prefix 字幕；不可猜測提問後內容。請產生嚴謹、適合指定年級的繁體中文 storyboard JSON。影片 30–90 秒，4–7 個場景；前 10 秒直接回答問題；明確指出迷思、用可計算或可視覺化的例子澄清，最後銜接原課程。不要模仿原講者。每個 scene 必須有 id、duration、title、body、narration、visual_prompt。只輸出 JSON，不要 markdown。"""
    user_text = {
        "case": case,
        "prefix_subtitles": subtitles,
        "constraints": {
            "language": "zh-TW", "disclaimer": DISCLAIMER,
            "duration_seconds": "30-90", "source_boundary": "prefix only"
        }
    }
    content = [{"type": "text", "text": json.dumps(user_text, ensure_ascii=False)}]
    for path in frame_paths[:6]:
        content.append({"type": "image_url", "image_url": {"url": image_data_url(path)}})
    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"storyboard API failed ({exc.code}): {detail}") from exc
    return clean_model_json(result["choices"][0]["message"]["content"])


def validate_storyboard(data):
    if data.get("language") != "zh-TW" or not data.get("scenes"):
        raise ValueError("storyboard must contain language=zh-TW and scenes")
    total = 0.0
    for index, scene in enumerate(data["scenes"], 1):
        required = ["id", "duration", "title", "body", "narration", "visual_prompt"]
        missing = [key for key in required if not scene.get(key)]
        if missing:
            raise ValueError(f"scene {index} missing: {', '.join(missing)}")
        if not re.fullmatch(r"scene_[0-9]{2,}", scene["id"]):
            raise ValueError(f"invalid scene id: {scene['id']}")
        total += float(scene["duration"])
    if not 30 <= total <= 90:
        raise ValueError(f"storyboard duration {total:.1f}s is outside 30–90s")
    data.setdefault("disclaimer", DISCLAIMER)
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="input")
    parser.add_argument("--work", default="work")
    parser.add_argument("--output", default=None)
    parser.add_argument("--model", default=os.environ.get("ASKBACK_LLM_MODEL", "gpt-4o-mini"))
    parser.add_argument("--offline-v08", action="store_true")
    args = parser.parse_args()
    input_dir, work_dir = pathlib.Path(args.input), pathlib.Path(args.work)
    work_dir.mkdir(parents=True, exist_ok=True)
    case = read_json(input_dir / "case_input.json")
    analysis_path = work_dir / "analysis.json"
    if not analysis_path.exists():
        raise SystemExit("run inspect_input.py before generate_storyboard.py")
    analysis = read_json(analysis_path)
    frame_dir = pathlib.Path(analysis["video"]["frame_dir"])
    frame_paths = sorted(frame_dir.glob("*.jpg"))
    try:
        if args.offline_v08 or case.get("case_id") == "V08" and not os.environ.get("OPENAI_API_KEY"):
            storyboard = reference_v08(case)
        else:
            storyboard = request_storyboard(case, bounded_subtitle(input_dir), frame_paths, args.model)
        storyboard = validate_storyboard(storyboard)
    except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"could not create storyboard: {exc}") from exc
    output = pathlib.Path(args.output) if args.output else work_dir / "storyboard.json"
    output.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(output), "scenes": len(storyboard["scenes"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
