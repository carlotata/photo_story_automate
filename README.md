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
photo_story_narrator/
├── input/
│   ├── shorts/                      # 📱 SHORT FORM (9:16 vertical, <= 59.0s max)
│   │   └── <Story Title>/           # Frame images & script.txt
│   └── long/                        # 🎬 LONG FORM (16:9 widescreen 2K)
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
├── run.py                           # CLI entrypoint supporting /shorts and /long
└── setup_model.py                   # Automatic Kokoro model downloader
```

---

## 🎬 Step-by-Step Production Workflow

The system is designed around dedicated **Short Form** and **Long Form** workflows:

### 📱 Short Form (9:16 Vertical, <= 59.0s Max Duration)
1. Drop images and `script.txt` into `input/shorts/<Story Title>/`.
2. Run:
   ```bash
   python run.py /shorts "Story Title"
   # Or simply type /shorts
   ```
3. Final 9:16 video is published to:
   ```
   output/shorts/<Story Title>/<Story Title>.mp4
   ```

### 🎬 Long Form (16:9 Widescreen 2K)
1. Drop images and `script.txt` into `input/long/<Story Title>/`.
2. Run:
   ```bash
   python run.py /long "Story Title"
   # Or simply type /long
   ```
3. Final 16:9 2K video is published to:
   ```
   output/long/<Story Title>/<Story Title>.mp4
   ```

---

### Step 1: Create Your Story Folder in `input/`
Create a story folder inside `input/` named after your project:
```
input/My Story Title/
```
Inside this folder, drop:
1. **Your Frame Images**: Can be named sequentially (`Frame_001.jpg`, `Frame_002.jpg`) or organized in segment subfolders (`s1/`, `s2/`, etc.). The engine automatically discovers all images and sorts them in natural numerical order.
2. **Your Script (`script.txt`)**: Text file containing your story narrative.

### Step 2: Format Your `script.txt`
You can write your script using standard plain text, the instructional assignment format, or paste full Episode Production Specs directly:

#### Format A: Instructional Assignment
```ini
# OPTIONAL INSTRUCTIONAL COMMENTS
# Any line starting with # or // is ignored.

SEGMENT 1: THE BEGINNING
Frame_001 = "You wake up to a buzzing alarm clock,"
Frame_002 = "stare at the ceiling,"
Frame_003 = "and calculate how many hours remain until Friday."
```

#### Format B: Full Episode Production Spec
You can paste full studio specs containing metadata, character turnarounds, environment descriptions, and a final `VOICEOVER:` block. The engine automatically parses the narration lines and pairs them with discovered frames.

#### 🛡️ Built-in Parser & Archive Guarantees:
- **Zero Image Tool Generation**: Frame images are generated externally and provided directly in the story folder or dropped as a `.zip` archive. The engine and agents never invoke browser or image generation tools.
- **Auto Zip Unpacking**: Dropping `EPISODE XX.zip` into `input/shorts/` automatically extracts into the story folder on pipeline execution.
- **Prefixes are stripped**: `Frame_001 =`, `- Frame_001 =`, or `FRAME 1 =` are automatically removed.
- **Headers & comments ignored**: `SEGMENT 1:` and `#` notes are skipped completely.
- **Narrator speaks only text**: Only the words inside the quotes or `VOICEOVER:` block are spoken by the voice actor.
- **1 Line = 1 Frame**: Frame $N$ corresponds directly to narration line $N$.

### Step 3: Choose Your Voice (11 Kokoro Voices Supported)
The repository defaults to **`am_adam` (Voice ID 5)** for clean, engaging narration. You can choose any of the 11 built-in voices via `--voice`:

| ID | Name | Accent | Gender | Tone & Best Use Case |
|:---:|:---|:---:|:---:|:---|
| **`5`** | **`am_adam`** | 🇺🇸 American | Male | **Repository Default**: Crisp, clear, conversational explainer |
| **`6`** | **`am_michael`** | 🇺🇸 American | Male | **Documentary Default**: Deep, cinematic, grounded authority |
| **`9`** | **`bm_george`** | 🇬🇧 British | Male | Deep, resonant, classical historical storyteller |
| **`10`** | **`bm_lewis`** | 🇬🇧 British | Male | Warm, composed, relaxed British narration |
| **`1`** | **`af_bella`** | 🇺🇸 American | Female | Warm, highly expressive, engaging character voice |
| **`4`** | **`af_sarah`** | 🇺🇸 American | Female | Confident, professional, modern corporate & tech voice |
| **`2`** | **`af_heart`** | 🇺🇸 American | Female | Soft, gentle, calm bedtime or reflective tone |
| **`3`** | **`af_nicole`** | 🇺🇸 American | Female | Subtle, intimate, whispery narrative tone |
| **`0`** | **`af_alloy`** | 🇺🇸 American | Female | Bright, upbeat, energetic pacing |
| **`7`** | **`bf_emma`** | 🇬🇧 British | Female | Articulate, refined British academic tone |
| **`8`** | **`bf_isabella`**| 🇬🇧 British | Female | Melodic, gentle British narrative tone |

### Step 4: Run the CLI
```bash
# Render with default voice (am_adam):
python run.py "My Story Title"

# Render with deep cinematic documentary voice (am_michael):
python run.py "My Story Title" --voice 6

# Render with dramatic British historical voice (bm_george):
python run.py "My Story Title" --voice 9

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
- **Universal Slash Commands & Pasted Specs (`/photoshorts`, `/photolong`, `/shorts`, `/long`)**: When the user provides a script or full Episode Spec (with or without a slash command prefix):
  1. Detect the episode title, target format (Shorts vs Long), and script lines.
  2. Create the target project folder: `input/shorts/<Title>/` or `input/long/<Title>/`.
  3. Save `script.txt` and `prompt_spec.txt`.
  4. Auto-detect any corresponding `.zip` file or folder, unpack archive, and clean up.
  5. Audit frame parity: verify that frame count equals script line count and that frames are in strict numerical sequence.
- **Zero External Image Generation**: Never use `browsentic`, browser automation, or image generation tools. Frames are pre-generated externally by the user and delivered directly or via auto-extracted zip files.
- **Voice Selection**: Always default to voice `5` (`am_adam`) for general workflows. For carlotata's personal local projects, default to voice `6` (`am_michael`).
- **Parity Invariant**: Ensure `len(discover_images(story_dir)) == len(clean_script_text(script_text))` before running.
- **Motion System**: Keep camera moves limited strictly to `zoom_in`, `pan_right`, and `static`.
- **Acoustic Alignment**: Never hardcode clip durations based on word estimates; rely on `align_narration_audio()` to measure real acoustic audio lengths.
- **Output Purity**: Do not generate extraneous preview files, CapCut drafts, or intermediate debug clips in `output/`.

---

## 🤝 Credits & Open-Source Acknowledgements

Photo Story Automate is built on top of incredible open-source research and engineering. Huge gratitude to the authors and maintainers of these projects:

- **[Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)** by **Hexgrad**: State-of-the-art 82M-parameter lightweight text-to-speech model with extraordinary naturalness and human-like prosody.
- **[sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)** by **Next-gen Kaldi / k2-fsa**: Blazing-fast, dependency-free offline speech processing engine enabling real-time Kokoro TTS on standard CPUs without GPU dependencies.
- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** by **SYSTRAN**: High-performance reimplementation of OpenAI's Whisper model via CTranslate2, powering microsecond-accurate acoustic forced alignment and word timestamps.
- **[OpenAI Whisper](https://github.com/openai/whisper)**: Robust speech recognition foundational models.
- **[FFmpeg](https://ffmpeg.org/)**: The swiss army knife of multimedia processing, providing high-precision Lanczos resampling, dynamic Zoompan Ken Burns transforms, and glitch-free Concat Demuxing.
- **[Pillow](https://python-pillow.org/)**: Python Imaging Library for non-destructive resolution probing, aspect ratio detection, and EXIF processing.
- **Typography**:
  - **[Poppins](https://github.com/itfoundry/Poppins)** by Indian Type Foundry (SIL Open Font License).
  - **[Anton](https://fonts.google.com/specimen/Anton)** by Vernon Adams (SIL Open Font License).
  - **[Bebas Neue](https://fonts.google.com/specimen/Bebas+Neue)** by Ryoichi Tsunekawa (SIL Open Font License).
- **[Antigravity CLI](https://github.com/google)**: Advanced agentic coding architecture and paired programming framework.

---

## 📜 License

MIT License. Free for personal, educational, and commercial video creation.
