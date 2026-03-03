# 🎬 Scene to Movie AI — Anime Creation Pipeline

An end-to-end, AI-powered pipeline that transforms a one-sentence story idea into a fully
rendered anime video — complete with generated visuals, animated scenes, voice-acted
dialogue, and professional post-production editing.

```
Story Idea
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1 │  Script Generation  (OpenAI GPT-4 / Anthropic)    │
└────────────────────────┬────────────────────────────────────┘
                         │  Script (scenes, characters, dialogue)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2 │  Character & Scene Design  (Stability AI SDXL)    │
└────────────────────────┬────────────────────────────────────┘
                         │  PNG images per scene
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3 │  Animation  (Pika Labs / Runway / OpenCV fallback)│
└────────────────────────┬────────────────────────────────────┘
                         │  MP4 video clips
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4 │  Voice Synthesis  (ElevenLabs)                    │
└────────────────────────┬────────────────────────────────────┘
                         │  Audio files per dialogue line
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5 │  Editing & Render  (FFmpeg)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                   final_export.mp4
```

---

## ✨ Features

- **AI Script Generation** — GPT-4 or Claude produces a structured, multi-scene anime
  script (characters, dialogue, mood cues) from a plain-English prompt.
- **AI Image Generation** — Stability AI SDXL creates character sheets and scene
  backgrounds in your chosen art style.
- **LoRA Support** — Register per-character LoRA weights for visual consistency.
- **Animation** — Pika Labs or Runway Gen-2 animate still images; local OpenCV
  Ken-Burns pan/zoom fallback requires no API key.
- **Voice Acting** — ElevenLabs synthesizes each dialogue line with character-specific
  voices; silent-WAV fallback when no key is set.
- **Post-Production** — FFmpeg handles audio mixing, subtitle burning, crossfade
  transitions, and H.264/AAC final export.
- **CLI Interface** — `click`-powered command line with `--prompt`, `--config`,
  `--steps`, `--resume` and more.
- **Step-level execution** — Run individual steps independently for rapid iteration.
- **Structured logging** — `rich`-powered coloured console output.
- **Pydantic v2 data models** — Strict typing throughout the pipeline.

---

## 📋 Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.10 |
| FFmpeg | ≥ 4.4 (must be in `PATH`) |
| OpenAI API key | For script generation (default) |
| Anthropic API key | Alternative script backend |
| Stability AI key | For image generation |
| Pika / Runway key | For cloud animation (optional) |
| ElevenLabs key | For voice synthesis (optional) |

> **Tip:** The pipeline runs without any API keys using local OpenCV animation and
> silent-audio placeholders — useful for testing the full flow.

---

## 🚀 Installation

```bash
# 1. Clone
git clone https://github.com/your-org/scene-to-movie-ai.git
cd scene-to-movie-ai

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys
cp .env.example .env
# Edit .env with your keys
```

Install FFmpeg:

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows — download from https://ffmpeg.org/download.html
```

---

## ⚡ Quick Start

```bash
python main.py --prompt "A lonely robot awakens in an abandoned city and searches for its creator"
```

This will:
1. Generate a 5-scene anime script
2. Create character and background artwork
3. Animate each scene
4. Synthesize dialogue audio
5. Render the final video to `output/<project>/video/final.mp4`

---

## 📖 Detailed Usage

### Full pipeline

```bash
python main.py \
  --prompt "Two rival ninjas must team up to stop an ancient dragon" \
  --config config.yaml \
  --num-scenes 6 \
  --output-dir output
```

### Run specific steps only

```bash
# Steps 1 and 2 only (script + design)
python main.py --prompt "..." --steps 1,2

# Step names also work
python main.py --prompt "..." --steps story,design
```

### Resume from an existing project

```bash
python main.py --resume output/my_project --steps 3,4,5
```

### Override logging level

```bash
python main.py --prompt "..." --log-level DEBUG
```

### Use a custom config file

```bash
python main.py --prompt "..." --config examples/example_config.yaml
```

---

## ⚙️ Configuration Reference

`config.yaml` controls every aspect of the pipeline:

```yaml
story:
  provider: "openai"          # "openai" | "anthropic"
  model: "gpt-4"              # model identifier
  temperature: 0.8            # 0.0–1.0 creativity
  num_scenes: 5               # scenes to generate

design:
  provider: "stability"       # "stability"
  model: "stable-diffusion-xl"
  style: "anime"              # injected into all prompts
  width: 1920
  height: 1080
  lora_models: []             # list of {character, path} dicts

animation:
  provider: "pika"            # "pika" | "runway" | "local"
  duration_per_scene: 5.0    # seconds
  fps: 24

voice:
  provider: "elevenlabs"
  default_model: "eleven_multilingual_v2"

editing:
  output_format: "mp4"
  resolution: "1920x1080"
  fps: 24
  codec: "h264"
  transition: "crossfade"     # "crossfade" | "cut"
  transition_duration: 0.5

output:
  base_dir: "output"
```

---

## 🏗️ Architecture

```
scene-to-movie-ai/
├── main.py                      # CLI entry point
├── config.yaml                  # Default configuration
├── requirements.txt
├── .env.example
├── pipeline/
│   ├── models.py                # Pydantic data models (Script, Scene, …)
│   ├── orchestrator.py          # AnimePipeline + PipelineConfig
│   ├── step1_story/             # LLM script generation
│   ├── step2_design/            # Stability AI image generation + LoRA
│   ├── step3_animation/         # Pika / Runway / OpenCV animation
│   ├── step4_voice/             # ElevenLabs voice synthesis
│   └── step5_editing/           # FFmpeg compositing, mixing, render
├── utils/
│   ├── logger.py                # Rich-powered structured logging
│   ├── file_manager.py          # Project directory management
│   └── api_client.py            # Async HTTP client with retry/rate-limit
├── output/                      # Generated files (git-ignored per project)
└── examples/                    # Sample story and config YAMLs
```

---

## 🔑 API Key Setup

Copy `.env.example` to `.env` and fill in your keys:

```dotenv
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
STABILITY_API_KEY=sk-...
PIKA_API_KEY=...
RUNWAY_API_KEY=...
ELEVENLABS_API_KEY=...
```

| Key | Where to get it |
|---|---|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ |
| `STABILITY_API_KEY` | https://platform.stability.ai/ |
| `PIKA_API_KEY` | https://pika.art/ |
| `RUNWAY_API_KEY` | https://runwayml.com/ |
| `ELEVENLABS_API_KEY` | https://elevenlabs.io/ |

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| `ffmpeg: command not found` | Install FFmpeg and ensure it's on your `PATH` |
| `OPENAI_API_KEY not set` | Add the key to `.env` or export as an env var |
| Stability images are placeholders | Add your `STABILITY_API_KEY` |
| Animation is just a pan/zoom | No Pika/Runway key — set `animation.provider: local` intentionally or add API keys |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Script JSON parse error | Increase `temperature` slightly or switch to `anthropic` provider |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes and add tests
4. Open a pull request describing your change

Please follow PEP 8 and add type hints to all public functions.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
