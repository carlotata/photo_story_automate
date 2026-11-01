"""Transition engine supporting purposeful cuts, dissolves, and batch stitching."""

import logging
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from .config import TransitionConfig, VideoConfig

logger = logging.getLogger("photo_story_narrator.transitions")

def stitch_clips_cut(
    clip_paths: List[Path],
    output_path: Path,
    temp_dir: Path
) -> Path:
    """Concatenates clips reliably via FFmpeg concat demuxer without command-line argument limits."""
    import shutil
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not clip_paths:
        raise ValueError("No clips to stitch.")
    if len(clip_paths) == 1:
        shutil.copy2(clip_paths[0], output_path)
        return output_path

    list_file = temp_dir / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            clean_path = str(p.resolve()).replace("\\", "/")
            f.write(f"file '{clean_path}'\n")

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg concat failed: {res.stderr}")

    return output_path

def stitch_batch_xfade(
    clips: List[Tuple[Path, float]], # List of (clip_path, duration)
    output_path: Path,
    trans_config: TransitionConfig,
    video_config: VideoConfig,
    transition_plan: Optional[List[Tuple[str, float]]] = None
) -> Path:
    """Stitches a batch of clips using purposeful transitions with exact offset math."""
    if not clips:
        raise ValueError("No clips to stitch.")
    if len(clips) == 1:
        import shutil
        shutil.copy2(clips[0][0], output_path)
        return output_path

    # Build transitions list
    if transition_plan and len(transition_plan) == len(clips) - 1:
        transitions = transition_plan
    else:
        # Fallback to config default
        transitions = []
        for i in range(len(clips) - 1):
            transitions.append(("cut", 0.0))

    all_cuts = all(t[0] == "cut" or t[1] <= 0.0 for t in transitions)
    if all_cuts:
        return stitch_clips_cut([c[0] for c in clips], output_path, output_path.parent)

    inputs = []
    for c_path, _ in clips:
        inputs.extend(["-i", str(c_path)])

    filter_complex = []
    last_v = "[0:v]"
    accum_dur = clips[0][1]

    for i in range(len(clips) - 1):
        next_v = f"[{i + 1}:v]"
        out_v = f"[v{i + 1}]" if i < len(clips) - 2 else "[v_final]"
        t_name, t_dur = transitions[i]
        next_clip_dur = clips[i + 1][1]

        if t_name == "cut" or t_dur <= 0.05:
            # 1-frame (0.04s) transition produces an instant hard cut
            t_name = "fade"
            t_dur = 0.04
        else:
            # Cinematic cross-dissolve with proper overlap math
            t_dur = min(t_dur, accum_dur * 0.45, next_clip_dur * 0.45)

        offset = max(0.01, accum_dur - t_dur)
        filter_complex.append(
            f"{last_v}{next_v}xfade=transition={t_name}:duration={t_dur:.3f}:offset={offset:.3f}{out_v}"
        )
        last_v = out_v
        accum_dur = offset + next_clip_dur

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error"
    ] + inputs + [
        "-filter_complex", ";".join(filter_complex),
        "-map", "[v_final]",
        "-c:v", "libx264",
        "-preset", video_config.preset,
        "-tune", getattr(video_config, "tune", "animation"),
        "-crf", str(video_config.crf),
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        logger.warning(f"xfade batch failed ({res.stderr}), falling back to direct cut concat.")
        return stitch_clips_cut([c[0] for c in clips], output_path, output_path.parent)

    return output_path
