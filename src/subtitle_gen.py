"""Fixed subtitle generator producing high-contrast animated ASS subtitles."""

from pathlib import Path
from typing import List, Dict, Any

from .config import SubtitleConfig, VideoConfig

SPEAKER_HIGHLIGHT_COLORS = {
    "narrator": "&H0020E5FF",      # Golden Yellow
    "default": "&H0020E5FF",
    "girl": "&H00B570FF",          # Vibrant Rose / Soft Coral Pink
    "female": "&H00B570FF",
    "woman": "&H00B570FF",
    "lady": "&H00B570FF",
    "mom": "&H00B570FF",
    "boy": "&H00FFAA33",           # Sky Cyan Blue
    "male": "&H00FFAA33",
    "man": "&H00FFAA33",
    "guy": "&H00FFAA33",
    "dad": "&H00FFAA33",
    "child": "&H0080FF70",         # Fresh Mint Green
    "kid": "&H0080FF70",
    "young_girl": "&H00B570FF",
    "announcement": "&H0033B0FF",  # Amber Alert Gold
    "announcer": "&H0033B0FF",
    "radio": "&H0033B0FF",
    "speaker": "&H0033B0FF",
    "system": "&H0033B0FF",
    "pa": "&H0033B0FF",
    "elder": "&H00E0E0E0",         # Soft Platinum Silver
}

def format_ass_time(seconds: float) -> str:
    """Formats float seconds into ASS timestamp H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

class SubtitleGenerator:
    def __init__(self, sub_config: SubtitleConfig, video_config: VideoConfig):
        self.sub_cfg = sub_config
        self.v_cfg = video_config

    def generate_ass(
        self,
        words_metadata: List[Dict[str, Any]],
        segments_metadata: List[Dict[str, Any]],
        output_ass_path: Path
    ) -> Path:
        """Generates an Advanced SubStation Alpha (.ass) file with fixed style and karaoke highlights."""
        output_ass_path = Path(output_ass_path)
        output_ass_path.parent.mkdir(parents=True, exist_ok=True)

        w = self.v_cfg.width
        h = self.v_cfg.height
        cfg = self.sub_cfg

        header = f"""[Script Info]
Title: PhotoStory Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {w}
PlayResY: {h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{cfg.font_name},{cfg.font_size},{cfg.primary_color},{cfg.highlight_color},{cfg.outline_color},{cfg.back_color},{cfg.bold},0,0,0,100,100,0,0,1,{cfg.outline_width},{cfg.shadow_depth},{cfg.alignment},50,50,{cfg.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        words_per_group = cfg.words_per_group

        if not words_metadata and segments_metadata:
            # Fallback to segment-level dialog lines
            for seg in segments_metadata:
                t0 = format_ass_time(seg["start"])
                t1 = format_ass_time(seg["end"])
                txt = seg["text"].upper()
                role = seg.get("speaker_role", "narrator")
                color = SPEAKER_HIGHLIGHT_COLORS.get(str(role).lower(), cfg.highlight_color)
                events.append(f"Dialogue: 0,{t0},{t1},Default,,0,0,0,,{{\\c{color}}}{txt}")
        else:
            # Word-level grouping with active highlight animation
            i = 0
            n_words = len(words_metadata)
            while i < n_words:
                group = words_metadata[i : i + words_per_group]
                # Active word highlight sequence
                for active_idx, active_w in enumerate(group):
                    w_start = format_ass_time(active_w["start"])
                    w_end = format_ass_time(active_w["end"])
                    active_role = active_w.get("speaker_role", "narrator")
                    active_color = SPEAKER_HIGHLIGHT_COLORS.get(str(active_role).lower(), cfg.highlight_color)

                    line_parts = []
                    for g_idx, g_w in enumerate(group):
                        clean_w = g_w["word"].upper()
                        if g_idx == active_idx:
                            # Highlighted word with role color + slight scale pop
                            line_parts.append(f"{{\\c{active_color}\\fscx106\\fscy106}}{clean_w}{{\\r}}")
                        else:
                            line_parts.append(f"{{\\c{cfg.primary_color}}}{clean_w}")

                    dialogue_text = " ".join(line_parts)
                    events.append(f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{dialogue_text}")

                i += len(group)

        full_content = header + "\n".join(events) + "\n"
        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        return output_ass_path
