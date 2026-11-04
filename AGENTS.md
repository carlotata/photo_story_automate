# AGENTS.md — Photo Story Narrator AI Agent Protocol

This file serves as the definitive reference for autonomous coding and operational agents (Claude Code, OpenAI Codex, Antigravity CLI, Cursor, etc.) working on or with **Photo Story Narrator**.

---

## 1. Project Mission & Overview

**Photo Story Narrator** is an automated 2K video production pipeline that converts static story illustrations (from 10 up to 1,000+ frames) and an audio script into a cinematic, fully voiced video:
- **TTS Engine**: Kokoro TTS via `sherpa-onnx` supporting 11 voices (0 to 10).
  - **Repository Default**: `am_adam` (ID: 5) for clean, crisp, conversational narration.
  - **Local Default (carlotata)**: `am_michael` (ID: 6) for deep, realistic cinematic documentary narration.
  - **Anishorts Default**: `am_adam` (ID: 5) for engaging social short narration.
- **Acoustic Forced Alignment**: `faster-whisper` (`tiny.en`) detects physical speech boundaries and places cuts strictly in natural acoustic silences between sentences: $\text{cut}_i = \frac{\text{speech\_end}_i + \text{speech\_start}_{i+1}}{2}$.
- **3 Clean Ken Burns Motions**:
  1. `zoom_in`: Centered slow push-in focusing attention on subjects.
  2. `pan_right`: Smooth horizontal tracking across landscapes and environments (Y locked center).
  3. `static`: Grounded stationary hold for quick flash gags & punchline beats (< 2.2s).
  *(All dizzying downward diagonal crawling is strictly forbidden).*
- **Subtitles**: Styled ASS subtitles with active-word karaoke pop, positioned bottom-center in safe areas.
- **Concat Demuxer**: Instantaneous acoustic hard cuts stitched via FFmpeg concat demuxer (`-f concat`) to prevent filter graph limits and EOF truncations.
- **Visual Purity**: Zero text badges, zero title overlays, zero UI cards on screen. Pristine animation.

---

## 2. Directory Layout & Categorized Workflow

The studio automatically separates **Short Form** and **Long Form** content:

```
photo_story_narrator/
├── input/
│   ├── shorts/                      # 📱 SHORT FORM CONTENT (9:16 vertical, <= 59.0s max)
│   │   └── <Story Title>/           # Frame images & script.txt
│   └── long/                        # 🎬 LONG FORM CONTENT (16:9 widescreen 2K)
│       └── <Story Title>/           # Frame images & script.txt
├── output/
│   ├── shorts/
│   │   └── <Story Title>/
│   │       └── <Story Title>.mp4    # Pristine 9:16 video (strictly <= 59.0s)
│   └── long/
│       └── <Story Title>/
│           └── <Story Title>.mp4    # Pristine 16:9 2K video
├── assets/
│   ├── fonts/Poppins-Bold.ttf       # Subtitle typography
│   └── kokoro-en-v0_19/             # ONNX model (installed via setup_model.py)
├── src/
│   ├── audio_aligner.py             # Whisper acoustic boundary alignment
│   ├── config.py                    # Global dataclass settings (Shorts vs Long presets)
│   ├── ken_burns.py                 # Centered Ken Burns motion filters
│   ├── scene_director.py            # Shot intent & audio cue director
│   ├── sfx_engine.py                # Diegetic narrative Foley mixer
│   ├── subtitle_gen.py              # ASS subtitle generation with word timings
│   ├── transitions.py               # Concat demuxer & transition router
│   ├── tts_engine.py                # Kokoro TTS with instructional script parser
│   ├── utils.py                     # Asset discovery & numerical frame sorting
│   └── video_assembler.py           # Pipeline orchestrator
├── AGENTS.md                        # Agent protocol specification
├── README.md                        # User documentation
├── requirements.txt                 # Python dependencies
├── run.py                           # CLI entrypoint supporting /shorts and /long
└── setup_model.py                   # One-click Kokoro ONNX model downloader
```

---

## 3. Format Specifications & Invariants

### 📱 Short Form (input/shorts/ -> output/shorts/)
- **Aspect Ratio**: 9:16 Vertical (`1440x2560`).
- **Maximum Duration**: **Strictly 59.0 seconds maximum**. Under NO circumstances can a short exceed 59.0 seconds.
- **Duration Auto-Protection**: If TTS voiceover exceeds 59.0s, the engine automatically applies FFmpeg audio tempo compression (`atempo`) targeting 58.5s and muxes with a `-t 59.0` hard clamp.
- **Voice Default**: `am_adam` (ID: 5) for punchy, high-retention social commentary.
- **Subtitles**: Bottom margin `margin_v=240` (safe zone above TikTok/Reels/Shorts UI), `font_size=68`, 3 words per karaoke pop.

### 🎬 Long Form (input/long/ -> output/long/)
- **Aspect Ratio**: 16:9 Widescreen 2K (`2560x1440`).
- **Duration**: Uncapped documentary format (from 2 minutes to 60+ minutes).
- **Voice Default**: `am_michael` (ID: 6) for deep, authoritative cinematic documentary narration.
- **Subtitles**: Bottom margin `margin_v=150`, `font_size=72`, 3 words per karaoke pop.

---

## 3. Script Parsing & Parity Rules

When authoring or verifying `script.txt`, agents must enforce the following rules:

### A. Format Support
Both standard plain-text (1 line = 1 frame) and instructional assignment syntax are natively supported:
```ini
# OPTIONAL RULES & COMMENTS
# Lines starting with # or // are ignored by TTS.

SEGMENT 1: THE DISCOVERY
Frame_001 = "You wake up to a buzzing alarm clock,"
Frame_002 = "stare at the ceiling,"
Frame_003 = "and calculate how many hours remain until Friday."
```

### B. What the Engine Automatically Strips (NEVER SPOKEN):
- The `Frame_XXX = ` or `- Frame_XXX = ` prefix.
- All comments (`#`, `//`).
- All segment headers (`SEGMENT 1: ...`).
- Only the clean text inside quotes is passed to Kokoro TTS.

### C. Parity Invariant:
- Total discovered frame images **MUST** equal total script lines:
  $$\text{count}(\text{images}) = \text{count}(\text{lines})$$
- Frame sorting uses numerical natural sorting (`Frame_001`, `Frame_002` ... `Frame_420`).

---

## 4. Execution Commands for Agents

### Setup & Dependencies:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download Kokoro TTS model (if not already present)
python setup_model.py

# 3. Verify FFmpeg is on PATH
ffmpeg -version
```

### Running the Pipeline:
```bash
# Render Short Form (9:16 vertical, <= 59.0s max):
python run.py /shorts "Sample Short Title"
# or run all shorts:
python run.py /shorts --all

# Render Long Form (16:9 widescreen 2K):
python run.py /long "How the concept of a job was invented"
# or run all long form stories:
python run.py /long --all

# Slash command shortcuts:
# Typing /shorts or /long lists and runs the respective category directly.
```

---

## 5. Anti-Bloat & Safety Laws for Agents
1. **Never exceed 59.0 seconds for Short Form**: Shorts must strictly stay <= 59.0s.
2. **Never export CapCut drafts** unless explicitly requested by the user.
3. **Never add on-screen badges, banners, or intro titles**; explainer cartoons must remain pristine.
4. **Never introduce diagonal Ken Burns camera paths**; only use `zoom_in`, `pan_right`, and `static`.
5. **Never truncate clips with xfade filters**; use the concat demuxer for flawless multi-hundred-frame stitching.
