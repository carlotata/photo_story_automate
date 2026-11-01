"""CapCut Draft Project Exporter.

Allows opening the assembled image timeline, transitions, and audio track
directly inside CapCut Desktop.
"""

import os
import json
import uuid
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("photo_story_narrator.capcut")

CAPCUT_DRAFT_ROOT = Path(r"C:\Users\carlo\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")

def export_to_capcut_draft(
    project_name: str,
    images: List[Path],
    durations: List[float],
    audio_path: Path,
    total_duration: float,
    fps: int = 25,
    width: int = 1080,
    height: int = 1920
) -> Path:
    """Exports the timeline into CapCut desktop draft folder so it appears in CapCut's project list."""
    if not CAPCUT_DRAFT_ROOT.exists():
        logger.info(f"CapCut draft folder not found at {CAPCUT_DRAFT_ROOT}. Skipping CapCut draft export.")
        return None

    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in project_name)
    draft_folder = CAPCUT_DRAFT_ROOT / safe_name
    draft_folder.mkdir(parents=True, exist_ok=True)

    draft_id = str(uuid.uuid4()).upper()
    now_us = int(time.time() * 1_000_000)
    total_us = int(total_duration * 1_000_000)

    # 1. Build Materials
    materials_videos = []
    materials_audios = []
    video_segments = []
    audio_segments = []

    cur_us = 0
    for idx, (img_p, dur_s) in enumerate(zip(images, durations)):
        dur_us = int(dur_s * 1_000_000)
        img_id = str(uuid.uuid4()).lower()
        seg_id = str(uuid.uuid4()).lower()
        p_str = str(img_p.resolve()).replace("\\", "/")

        materials_videos.append({
            "id": img_id,
            "type": "photo",
            "path": p_str,
            "duration": dur_us,
            "material_name": img_p.name,
            "width": width,
            "height": height
        })

        video_segments.append({
            "id": seg_id,
            "material_id": img_id,
            "source_timerange": {"start": 0, "duration": dur_us},
            "target_timerange": {"start": cur_us, "duration": dur_us},
            "render_index": 0
        })
        cur_us += dur_us

    # Audio material
    if audio_path and audio_path.exists():
        audio_id = str(uuid.uuid4()).lower()
        audio_seg_id = str(uuid.uuid4()).lower()
        a_str = str(audio_path.resolve()).replace("\\", "/")
        materials_audios.append({
            "id": audio_id,
            "type": "extract_music",
            "name": audio_path.name,
            "path": a_str,
            "duration": total_us
        })
        audio_segments.append({
            "id": audio_seg_id,
            "material_id": audio_id,
            "source_timerange": {"start": 0, "duration": total_us},
            "target_timerange": {"start": 0, "duration": total_us}
        })

    # Draft content structure
    draft_content = {
        "id": draft_id,
        "name": safe_name,
        "duration": total_us,
        "fps": fps,
        "canvas_config": {"width": width, "height": height, "ratio": "original"},
        "materials": {
            "videos": materials_videos,
            "audios": materials_audios,
            "texts": [],
            "transitions": []
        },
        "tracks": [
            {
                "id": str(uuid.uuid4()).lower(),
                "type": "video",
                "segments": video_segments
            },
            {
                "id": str(uuid.uuid4()).lower(),
                "type": "audio",
                "segments": audio_segments
            }
        ]
    }

    # Draft meta info
    draft_meta = {
        "draft_id": draft_id,
        "draft_name": safe_name,
        "draft_fold_path": str(draft_folder).replace("\\", "/"),
        "draft_root_path": str(CAPCUT_DRAFT_ROOT).replace("\\", "/"),
        "tm_draft_create": now_us,
        "tm_draft_modified": now_us,
        "tm_duration": total_us
    }

    with open(draft_folder / "draft_content.json", "w", encoding="utf-8") as f:
        json.dump(draft_content, f, indent=2)

    with open(draft_folder / "draft_meta_info.json", "w", encoding="utf-8") as f:
        json.dump(draft_meta, f, indent=2)

    logger.info(f"CapCut Draft exported successfully to: {draft_folder}")
    return draft_folder
