"""Fixed subtitle generator producing high-contrast animated ASS subtitles."""

from pathlib import Path
from typing import List, Dict, Any

from .config import SubtitleConfig, VideoConfig

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
                events.append(f"Dialogue: 0,{t0},{t1},Default,,0,0,0,,{txt}")
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

                    line_parts = []
                    for g_idx, g_w in enumerate(group):
                        clean_w = g_w["word"].upper()
                        if g_idx == active_idx:
                            # Highlighted word: Golden Yellow + slight scale pop
                            line_parts.append(f"{{\\c{cfg.highlight_color}\\fscx106\\fscy106}}{clean_w}{{\\r}}")
                        else:
                            line_parts.append(f"{{\\c{cfg.primary_color}}}{clean_w}")

                    dialogue_text = " ".join(line_parts)
                    events.append(f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{dialogue_text}")

                i += len(group)

        full_content = header + "\n".join(events) + "\n"
        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        return output_ass_path
