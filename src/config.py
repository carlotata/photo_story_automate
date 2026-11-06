"""Configuration settings for Photo Story Narrator."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent

# Resolve Kokoro model path
def find_kokoro_model_dir() -> Path:
    candidates = [
        PROJECT_ROOT / "assets" / "kokoro-en-v0_19",
        WORKSPACE_ROOT / "anishorts" / "assets" / "kokoro-en-v0_19",
        WORKSPACE_ROOT / "ani_shorts_stickman" / "kokoro-en-v0_19",
    ]
    for c in candidates:
        if (c / "model.onnx").exists() and (c / "voices.bin").exists():
            return c
    return PROJECT_ROOT / "assets" / "kokoro-en-v0_19"

# Resolve font path
def find_font_path() -> Path:
    candidates = [
        PROJECT_ROOT / "assets" / "fonts" / "Poppins-Bold.ttf",
        WORKSPACE_ROOT / "anishorts" / "assets" / "fonts" / "Poppins-Bold.ttf",
        WORKSPACE_ROOT / "ani_shorts_stickman" / "fonts" / "Poppins-Bold.ttf",
    ]
    for c in candidates:
        if c.exists():
            return c
    return PROJECT_ROOT / "assets" / "fonts" / "Poppins-Bold.ttf"

@dataclass
class VideoConfig:
    width: int = 2560
    height: int = 1440
    fps: int = 25
    crf: int = 18
    preset: str = "fast"
    tune: str = "animation"
    scaling_flags: str = "lanczos+accurate_rnd"
    bitrate: str = "18000k"

# Semantic voice role mappings for Kokoro
VOICE_ROLE_MAPPING: Dict[str, int] = {
    # Default narrator
    "narrator": 6,        # am_michael (cinematic documentary male)
    "default": 6,
    # Female / Girl
    "girl": 1,            # af_bella (warm & expressive)
    "female": 1,
    "woman": 1,
    "lady": 1,
    "mom": 1,
    "mother": 1,
    "sister": 1,
    "daughter": 1,
    # Male / Boy
    "boy": 5,             # am_adam (crisp & conversational)
    "male": 5,
    "man": 5,
    "guy": 5,
    "dad": 5,
    "father": 5,
    "brother": 5,
    "son": 5,
    # Kid / Child / Young
    "child": 2,           # af_heart (soft & calm)
    "kid": 3,             # af_nicole (gentle)
    "young_girl": 3,
    "young_boy": 5,
    # Announcement / Radio / PA / Official
    "announcement": 9,    # bm_george (deep & resonant British male)
    "announcer": 9,
    "radio": 9,
    "intercom": 9,
    "pa": 9,
    "broadcast": 9,
    "speaker": 9,
    "system": 9,
    "ai": 0,              # af_alloy (neutral clean synthetic)
    "robot": 0,
    # Elder / Mentor
    "elder": 10,          # bm_lewis (smooth composed)
    "wise": 10,
    "mentor": 10,
    "grandfather": 10,
    # Direct Kokoro voice names
    "af_alloy": 0,
    "af_bella": 1,
    "af_heart": 2,
    "af_nicole": 3,
    "af_sarah": 4,
    "am_adam": 5,
    "am_michael": 6,
    "bf_emma": 7,
    "bf_isabella": 8,
    "bm_george": 9,
    "bm_lewis": 10,
}

@dataclass
class VoiceConfig:
    # Kokoro voice IDs:
    # 0: af_alloy (American Female)
    # 1: af_bella (American Female - Warm & Expressive)
    # 2: af_heart (American Female - Soft & Calm)
    # 3: af_nicole (American Female - Gentle)
    # 4: af_sarah (American Female - Confident)
    # 5: am_adam (American Male - Crisp & Conversational, Repository Default)
    # 6: am_michael (American Male - Deep Documentary Narrator, Local Default)
    # 7: bf_emma (British Female - Articulate)
    # 8: bf_isabella (British Female - Melodic)
    # 9: bm_george (British Male - Deep & Resonant Historical)
    # 10: bm_lewis (British Male - Smooth & Composed)
    speaker_id: int = 6
    speaker_name: str = "am_michael"
    speed: float = 1.02
    model_dir: Path = field(default_factory=find_kokoro_model_dir)
    custom_cast: Dict[str, str] = field(default_factory=dict)

@dataclass
class SubtitleConfig:
    font_path: Path = field(default_factory=find_font_path)
    font_name: str = "Poppins"
    font_size: int = 48
    primary_color: str = "&H00FFFFFF"     # Crisp White (AABBGGRR in ASS)
    highlight_color: str = "&H0020E5FF"   # Electric Golden Yellow
    outline_color: str = "&H00000000"     # Pitch Black
    back_color: str = "&H60000000"        # 38% Alpha Black Shadow
    bold: int = 1
    outline_width: float = 3.8
    shadow_depth: float = 2.0
    alignment: int = 2                     # Bottom Center
    margin_v: int = 140                    # Bottom safe area margin
    words_per_group: int = 3               # Fast-reading 3-4 words per caption card

@dataclass
class KenBurnsConfig:
    zoom_min: float = 1.0
    zoom_max: float = 1.06
    oversample_factor: float = 1.05        # Optimized scaling factor for high-speed rendering
    motion_types: Tuple[str, ...] = (
        "zoom_in",
        "pan_right",
        "static"
    )

@dataclass
class TransitionConfig:
    # Allowed xfade transitions: 'cut', 'hblur', 'dissolve', 'zoomin', 'wipeleft', 'slideleft', 'fadewhite'
    default_transition: str = "random_cinematic"
    cinematic_palette: Tuple[str, ...] = ("hblur", "dissolve", "zoomin", "slideleft")
    normal_duration: float = 0.40          # seconds
    short_duration: float = 0.20           # for rapid slides (< 1.5s)
    micro_threshold: float = 0.70          # below this duration, force direct cut

@dataclass
class StoryConfig:
    input_dir: Path = PROJECT_ROOT / "input"
    input_shorts_dir: Path = PROJECT_ROOT / "input" / "shorts"
    input_shorts_pending: Path = PROJECT_ROOT / "input" / "shorts" / "pending"
    input_shorts_completed: Path = PROJECT_ROOT / "input" / "shorts" / "completed"
    input_long_dir: Path = PROJECT_ROOT / "input" / "long"
    input_long_pending: Path = PROJECT_ROOT / "input" / "long" / "pending"
    input_long_completed: Path = PROJECT_ROOT / "input" / "long" / "completed"
    output_dir: Path = PROJECT_ROOT / "output"
    output_shorts_dir: Path = PROJECT_ROOT / "output" / "shorts"
    output_long_dir: Path = PROJECT_ROOT / "output" / "long"
    work_dir: Path = PROJECT_ROOT / "work"
    assets_dir: Path = PROJECT_ROOT / "assets"
    content_format: str = "auto"          # "auto", "shorts", or "long"
    max_duration: Optional[float] = None  # 59.0s maximum enforced for shorts
    video: VideoConfig = field(default_factory=VideoConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    subtitle: SubtitleConfig = field(default_factory=SubtitleConfig)
    ken_burns: KenBurnsConfig = field(default_factory=KenBurnsConfig)
    transition: TransitionConfig = field(default_factory=TransitionConfig)
    chunk_batch_size: int = 300
    render_workers: int = 4
