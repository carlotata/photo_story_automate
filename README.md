# Photo Story Automate 🎬

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FFmpeg](https://img.shields.io/badge/ffmpeg-8.0+-green.svg)](https://ffmpeg.org/)
[![Kokoro TTS](https://img.shields.io/badge/TTS-Kokoro--ONNX-orange.svg)](https://github.com/k2-fsa/sherpa-onnx)
[![faster-whisper](https://img.shields.io/badge/ASR-faster--whisper-purple.svg)](https://github.com/SYSTRAN/faster-whisper)
[![Resolution](https://img.shields.io/badge/Output-2560x1440%20(2K)-red.svg)](#)

An automated production studio that transforms static illustrations (from 10 up to 1,000+ frames) and narration scripts into cinematic, fully voiced videos with **deep realistic male narration**, **acoustic waveform-locked cuts**, **non-distracting camera motion**, and **active-word karaoke subtitles**.

Designed to run completely autonomously via standard terminal commands or through AI coding agents like **Claude Code**, **OpenAI Codex**, and **Antigravity CLI**.

---

## 🌟 Key Features

- **🎙️ Kokoro Deep Male Voiceover**: Offline, ultra-realistic narration using `sherpa-onnx` Kokoro models (`am_michael` deep American male, `bm_george` resonant British male).
- **⏱️ Acoustic Forced Alignment**: Uses `faster-whisper` (`tiny.en`) to pinpoint physical speech boundaries and place video cuts precisely in natural acoustic pauses ($\text{cut}_i = \frac{\text{speech\_end}_i + \text{speech\_start}_{i+1}}{2}$).
- **🎥 3 Clean Ken Burns Motions**:
  - `zoom_in`: Smooth, centered slow push-in focusing viewer attention.
  - `pan_right`: Pure horizontal landscape tracking across the X-axis (Y locked center).
  - `static`: Grounded stationary hold for quick punchlines and flash beats (< 2.2s).
  *(All dizzying downward diagonal crawling is strictly eliminated).*
- **💬 Active-Word Karaoke Subtitles**: Dynamic ASS subtitles rendered with Poppins-Bold typography and active-word gold pop highlights, locked to safe reading areas.
- **⚡ Concat Demuxer Engine**: Instantaneous acoustic hard cuts stitched via FFmpeg concat demuxer (`-f concat`) to prevent filter graph limits and EOF truncations across hundreds of clips.
- **✨ Clean Visual Purity**: Zero watermarks, zero text badges, zero title overlays. Only your artwork and synced subtitles appear on screen.

---

## 📁 Repository Structure

```
photo_story_automate/
├── input/
│   └── <Story Title>/               # Story directory
│       ├── s1/ ... sN/ or *.jpg     # Frame images sorted numerically
│       └── script.txt               # Narration script
├── output/
│   └── <Story Title>/
│       └── <Story Title>.mp4        # Pristine 2K final video ONLY
├── assets/
│   ├── fonts/Poppins-Bold.ttf       # Subtitle typography
│   └── kokoro-en-v0_19/             # ONNX model (installed via setup_model.py)
├── src/
│   ├── audio_aligner.py             # Whisper acoustic boundary alignment
│   ├── config.py                    # Global video & audio configuration
│   ├── ken_burns.py                 # Centered Ken Burns motion filters
│   ├── scene_director.py            # Shot intent & audio cue director
│   ├── sfx_engine.py                # Diegetic narrative Foley mixer
│   ├── subtitle_gen.py              # ASS subtitle generation with word timings
│   ├── transitions.py               # Concat demuxer & transition router
│   ├── tts_engine.py                # Kokoro TTS with instructional script parser
│   ├── utils.py                     # Asset discovery & numerical frame sorting
│   └── video_assembler.py           # Pipeline orchestrator
├── AGENTS.md                        # CLI agent operating protocol
├── README.md                        # Documentation
├── requirements.txt                 # Python dependencies
├── run.py                           # CLI entrypoint
└── setup_model.py                   # Automatic Kokoro model downloader
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python**: 3.10 or higher.
- **FFmpeg**: Must be installed and available on your system `PATH`.
  ```bash
  ffmpeg -version
  ```

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/carlotata/photo_story_automate.git
cd photo_story_automate

# Install Python requirements
pip install -r requirements.txt

# Download Kokoro TTS ONNX model (~330MB)
python setup_model.py
```

---

## 🎬 How to Run

### Step 1: Create Your Story Folder
Create a story folder inside `input/`, for example:
```
input/My Story Title/
```
Drop your image files (`Frame_001.jpg`, `Frame_002.jpg`, or subfolders `s1/`, `s2/`, etc.) and your `script.txt` inside.

### Step 2: Format Your `script.txt`
You can write your script using standard instructional assignment format:
```ini
# OPTIONAL INSTRUCTIONAL COMMENTS
# Any line starting with # or // is ignored.

SEGMENT 1: THE BEGINNING
Frame_001 = "You wake up to a buzzing alarm clock,"
Frame_002 = "stare at the ceiling,"
Frame_003 = "and calculate how many hours remain until Friday."
```

#### 🛡️ Built-in Parser Guarantees:
- **Prefixes are stripped**: `Frame_001 =`, `- Frame_001 =`, or `FRAME 1 =` are automatically removed.
- **Headers & comments ignored**: `SEGMENT 1:` and `#` notes are skipped completely.
- **Narrator speaks only text**: Only the words inside the quotes are spoken by the voice actor.
- **1 Line = 1 Frame**: Frame $N$ corresponds directly to narration line $N$.

### Step 3: Run the CLI
```bash
# Render a specific story:
python run.py "My Story Title"

# Render with specific voice (6 = Deep American Narrator, 9 = Deep British Narrator):
python run.py "My Story Title" --voice 6

# Render all stories inside input/:
python run.py --all
```

Your completed video will be saved directly into:
```
output/My Story Title/My Story Title.mp4
```

---

## 🤖 CLI Agent Operating Guide (Claude Code, Codex, Antigravity)

If you are an autonomous coding agent executing or extending this codebase, adhere strictly to [AGENTS.md](AGENTS.md):
- **Parity Invariant**: Ensure `len(discover_images(story_dir)) == len(clean_script_text(script_text))` before running.
- **Motion System**: Keep camera moves limited strictly to `zoom_in`, `pan_right`, and `static`.
- **Acoustic Alignment**: Never hardcode clip durations based on word estimates; rely on `align_narration_audio()` to measure real acoustic audio lengths.
- **Output Purity**: Do not generate extraneous preview files, CapCut drafts, or intermediate debug clips in `output/`.

---

## 📜 License

MIT License. Free for personal, educational, and commercial video creation.
