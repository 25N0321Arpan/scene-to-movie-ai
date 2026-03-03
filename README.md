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

- **AI Script Generation** — GPT-4, Claude, or **Gemini 2.0 Flash (free)** produces a
  structured, multi-scene anime script (characters, dialogue, mood cues) from a plain-English
  prompt.
- **AI Image Generation** — Stability AI SDXL or **Hugging Face Inference API (free)** creates
  character sheets and scene backgrounds in your chosen art style.
- **LoRA Support** — Register per-character LoRA weights for visual consistency.
- **Animation** — Pika Labs or Runway Gen-2 animate still images; local OpenCV
  Ken-Burns pan/zoom fallback requires no API key.
- **Voice Acting** — ElevenLabs synthesizes each dialogue line with character-specific
  voices; **Edge TTS (completely free, 300+ voices)** is the default; silent-WAV fallback
  when no key is set.
- **Post-Production** — FFmpeg handles audio mixing, subtitle burning, crossfade
  transitions, and H.264/AAC final export.
- **CLI Interface** — `click`-powered command line with `--prompt`, `--config`,
  `--steps`, `--resume` and more.
- **Step-level execution** — Run individual steps independently for rapid iteration.
- **Structured logging** — `rich`-powered coloured console output.
- **Pydantic v2 data models** — Strict typing throughout the pipeline.

---

## 🆓 Free Mode

Run the **entire pipeline for free** — no credit card required.

| Step | Free Provider | Key Required? |
|---|---|---|
| Script Generation | Google Gemini 2.0 Flash | ✅ Free key from [aistudio.google.com](https://aistudio.google.com) |
| Image Generation | Hugging Face Inference API | ⚡ Optional (many models work without auth) |
| Animation | Local OpenCV | ❌ No key needed |
| Voice Synthesis | Edge TTS | ❌ No key needed — 300+ voices |
| Editing & Render | FFmpeg | ❌ No key needed |

### Quick Start (Free Mode)

```bash
# 1. Get a free Gemini key from https://aistudio.google.com
# 2. Add to .env:
echo "GOOGLE_API_KEY=your_key" > .env

# 3. Run!
python main.py --prompt "A samurai discovers a hidden digital world"
```

Free tier limits: Gemini gives 15 requests/min and 1 M tokens/day — more than enough for a full
anime episode.

---

## 📋 Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.10 |
| FFmpeg | ≥ 4.4 (must be in `PATH`) |
| Google API key | For Gemini script generation (free default) |
| OpenAI API key | Alternative script backend (paid) |
| Anthropic API key | Alternative script backend (paid) |
| Hugging Face key | For HF image generation (optional, free) |
| Stability AI key | Alternative image backend (paid) |
| Pika / Runway key | For cloud animation (optional, paid) |
| ElevenLabs key | For ElevenLabs voice synthesis (optional, paid) |

> **Tip:** With just a free Google Gemini API key you get a fully working pipeline —
> Hugging Face image generation, local OpenCV animation, and Edge TTS voice synthesis
> all need no additional keys.

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
  provider: "gemini"          # "gemini" (free) | "openai" | "anthropic"
  model: "gemini-2.0-flash"   # model identifier
  temperature: 0.8            # 0.0–1.0 creativity
  num_scenes: 5               # scenes to generate

design:
  provider: "huggingface"     # "huggingface" (free) | "stability"
  model: "stabilityai/stable-diffusion-xl-base-1.0"
  style: "anime"              # injected into all prompts
  width: 1024
  height: 1024
  lora_models: []             # list of {character, path} dicts

animation:
  provider: "local"           # "local" (free) | "pika" | "runway"
  duration_per_scene: 5.0    # seconds
  fps: 24

voice:
  provider: "edge-tts"        # "edge-tts" (free) | "elevenlabs"
  default_model: "en-US-AriaNeural"

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
# === FREE PROVIDERS (recommended) ===
GOOGLE_API_KEY=your_free_gemini_key_here
HUGGINGFACE_API_KEY=your_free_hf_key_here

# === PAID PROVIDERS (optional) ===
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
STABILITY_API_KEY=sk-...
PIKA_API_KEY=...
RUNWAY_API_KEY=...
ELEVENLABS_API_KEY=...
```

| Key | Where to get it | Cost |
|---|---|---|
| `GOOGLE_API_KEY` | https://aistudio.google.com | Free |
| `HUGGINGFACE_API_KEY` | https://huggingface.co/settings/tokens | Free |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys | Paid |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ | Paid |
| `STABILITY_API_KEY` | https://platform.stability.ai/ | Paid |
| `PIKA_API_KEY` | https://pika.art/ | Paid |
| `RUNWAY_API_KEY` | https://runwayml.com/ | Paid |
| `ELEVENLABS_API_KEY` | https://elevenlabs.io/ | Paid |

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| `ffmpeg: command not found` | Install FFmpeg and ensure it's on your `PATH` |
| `OPENAI_API_KEY not set` | Add the key to `.env` or switch to the free Gemini provider |
| `GOOGLE_API_KEY not set` | Get a free key from https://aistudio.google.com |
| Stability images are placeholders | Add your `STABILITY_API_KEY` or switch to `design.provider: huggingface` |
| Animation is just a pan/zoom | No Pika/Runway key — this is expected with `animation.provider: local` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Script JSON parse error | Increase `temperature` slightly or switch provider |
| Edge TTS not found | Run `pip install edge-tts` |

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
