# AskBack AI Teacher Skill

這是一個給 Codex、Claude Code 等 coding agent 使用的 AI 老師 skill。它會讀取執行目錄下的 `input/`，針對學生在原教學影片中途提出的問題，產生一支 30–90 秒、繁體中文、有畫面與語音的補充教學影片。

## 給執行本 repo 的 agent

請完整閱讀 [`SKILL.md`](SKILL.md)，再按照其中的流程執行。不要要求使用者補充另一份提示；`input/` 內的 `case_input.json`、`prefix.mp4` 與可選的 `prefix.vtt` 就是唯一輸入。

最短流程如下（有 `OPENAI_API_KEY` 時可直接端到端執行）：

```bash
python3 scripts/run_pipeline.py --input input --work work --output outputs/askback.mp4
```

`run_pipeline.py` 會依序檢查輸入、產生 storyboard、呼叫 OpenAI-compatible
Chat Completions 分析代表畫面、用 OpenAI Speech API 產生繁中語音、渲染並驗證
MP4。預設讀取 `OPENAI_API_KEY`；可用 `OPENAI_BASE_URL`、`ASKBACK_LLM_MODEL`、
`ASKBACK_TTS_MODEL` 和 `ASKBACK_TTS_VOICE` 改用相容端點或指定模型。金鑰只從
環境變數讀取，不會寫進檔案。

如果執行環境的 agent 本身已經能理解影片並產生 TTS，agent 可以手動建立
`work/storyboard.json` 與 `work/audio/scene_XX.wav`，再執行 `render_video.py` 和
`validate_output.py`。沒有 TTS 金鑰時，程式會明確停止，不會用靜音或測試音效冒充教學語音。

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
