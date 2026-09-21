# AskBack AI Teacher Skill

這是一個給 Codex、Claude Code 等 coding agent 使用的 AI 老師 skill。它會讀取執行目錄下的 `input/`，針對學生在原教學影片中途提出的問題，產生一支 30–90 秒、繁體中文、有畫面與語音的補充教學影片。

## 給執行本 repo 的 agent

請完整閱讀 [`SKILL.md`](SKILL.md)，再按照其中的流程執行。不要要求使用者補充另一份提示；`input/` 內的 `case_input.json`、`prefix.mp4` 與可選的 `prefix.vtt` 就是唯一輸入。

最短流程如下：

```bash
python3 scripts/inspect_input.py --input input --work work
# 讀取 work/analysis.json、work/frames/ 與 input/case_input.json
# 以 agent 的多模態/音訊能力理解影片，建立 work/storyboard.json
# 產生 work/audio/scene_XX.wav（使用可用的 TTS 工具）
python3 scripts/render_video.py \
  --storyboard work/storyboard.json \
  --workdir work \
  --output outputs/askback.mp4
python3 scripts/validate_output.py outputs/askback.mp4
```

如果系統沒有套件：

```bash
python3 -m pip install -r requirements.txt
```

## 輸入與輸出

輸入必須位於：

```text
input/
├── case_input.json
├── prefix.mp4
└── prefix.vtt       # 沒有字幕的題目可以不存在
```

輸出固定放在 `outputs/askback.mp4`。影片必須：

- 長度 30–90 秒；
- 有清楚的繁體中文語音與可讀畫面；
- 片頭或固定角標標明「AI 生成教學示範，非原講者本人」；
- 只使用提問時間以前的 `prefix.mp4` / `prefix.vtt`，不可讀取完整原片或答案資料；
- 回答學生真正的迷思，並符合年段、科目與原影片的教學風格；
- 不模仿原講者的聲音或肖像。

## 本地測試

將作業提供的一題資料放成 `input/` 後執行上述流程。`scripts/inspect_input.py` 會擷取代表畫面與影片 metadata；`scripts/render_video.py` 會把 storyboard 和 TTS 音檔穩定合成 MP4。

完整的教育內容判斷、腳本撰寫、畫面素材生成與 TTS 供應商選擇，請遵照 `SKILL.md`。不要把 API key 寫入 repo。

