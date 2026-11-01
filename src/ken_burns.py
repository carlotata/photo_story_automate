"""Butter-Smooth Centered Ken Burns Engine.

Restricted to professional, non-distracting camera moves:
- Clean Centered Push-In (zoom_in)
- Clean Centered Pull-Out (zoom_out)
- Pure Horizontal Pan (pan_right / pan_left)
- Grounded Static (static)

Zero diagonal crawling, zero off-axis drifting, and continuous cosine easing.
"""

import math
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any

from .config import KenBurnsConfig, VideoConfig

logger = logging.getLogger("photo_story_narrator.ken_burns")

def get_ken_burns_filter(
    motion_type: str,
    duration: float,
    video_config: VideoConfig,
    kb_config: KenBurnsConfig
) -> str:
    """
    Constructs a clean, centered, jitter-free Ken Burns filter graph.
    Eliminates all diagonal drifting so the viewer's gaze remains naturally anchored.
    """
    w = video_config.width
    h = video_config.height
    fps = video_config.fps
    num_frames = max(1, int(round(duration * fps)))

    # Compute high-density oversampled canvas (7680px long-edge)
    if w >= h:
        base_w = 7680
        base_h = int(round(7680 * (h / float(w))))
    else:
        base_h = 7680
        base_w = int(round(7680 * (w / float(h))))

    # Step 1: High-res scale & center crop with pristine Lanczos filtering
    scaling_flags = getattr(video_config, "scaling_flags", "lanczos+accurate_rnd")
    prep = (
        f"scale={base_w}:{base_h}:flags={scaling_flags}:force_original_aspect_ratio=increase,"
        f"crop={base_w}:{base_h}"
    )

    z_min = kb_config.zoom_min
    z_max = kb_config.zoom_max
    z_range = z_max - z_min

    # Cosine easing formula: alpha = 0.5 - 0.5 * cos(PI * on / N)
    ease_curve = f"(0.5-0.5*cos(PI*on/{num_frames}))"

    if motion_type == "zoom_in":
        # Pure centered slow push-in (anchored at optical center)
        zp = (
            f"zoompan=z='{z_min:.4f}+{z_range:.4f}*{ease_curve}':d={num_frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}"
        )
    elif motion_type == "zoom_out":
        # Pure centered slow pull-back (anchored at optical center)
        zp = (
            f"zoompan=z='{z_max:.4f}-{z_range:.4f}*{ease_curve}':d={num_frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}"
        )
    elif motion_type == "pan_right":
        # Pure horizontal glide across the X-axis (Y remains locked in center)
        pan_zoom = 1.05
        zp = (
            f"zoompan=z={pan_zoom}:d={num_frames}:"
            f"x='{ease_curve}*(iw-iw/zoom)':"
            f"y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}"
        )
    elif motion_type == "pan_left":
        # Pure horizontal glide across the X-axis (Y remains locked in center)
        pan_zoom = 1.05
        zp = (
            f"zoompan=z={pan_zoom}:d={num_frames}:"
            f"x='(1.0-{ease_curve})*(iw-iw/zoom)':"
            f"y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}"
        )
    else:  # static / micro_focus
        # Perfectly still shot with dead-center lock (ideal for quick flash gags & titles)
        zp = (
            f"zoompan=z=1.0:d={num_frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}"
        )

    return f"{prep},{zp}"

def render_image_clip(
    image_path: Path,
    output_clip_path: Path,
    duration: float,
    motion_type: str,
    video_config: VideoConfig,
    kb_config: KenBurnsConfig
) -> Path:
    """Renders a single static image into a high-quality video clip with Ken Burns effect."""
    output_clip_path = Path(output_clip_path)
    output_clip_path.parent.mkdir(parents=True, exist_ok=True)

    vf = get_ken_burns_filter(motion_type, duration, video_config, kb_config)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", vf,
        "-t", f"{duration:.3f}",
        "-c:v", "libx264",
        "-preset", video_config.preset,
        "-tune", getattr(video_config, "tune", "animation"),
        "-crf", str(video_config.crf),
        "-pix_fmt", "yuv420p",
        str(output_clip_path)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg Ken Burns failed for {image_path.name}: {res.stderr}")

    return output_clip_path
