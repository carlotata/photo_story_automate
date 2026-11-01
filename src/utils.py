"""Utility helpers for image discovery, story detection, natural sorting, and duration calculations."""

import re
import os
import shutil
import logging
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger("photo_story_narrator.utils")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

def natural_sort_key(s: str):
    """Sort strings containing numbers in human order (e.g., img2 before img10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", str(s))]

def sanitize_title(title: str) -> str:
    """Removes invalid filename characters from story title."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", title).strip()
    return cleaned if cleaned else "Untitled_Story"

def discover_stories(input_root: Path) -> List[Path]:
    """Finds all story subdirectories inside input/ that contain images or files."""
    input_root = Path(input_root)
    if not input_root.exists():
        return []

    stories = []
    for item in sorted(input_root.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            # Check if directory contains images
            imgs = discover_images(item)
            if imgs:
                stories.append(item)
    return stories

def frame_sort_key(p: Path):
    """Sorts images by explicit frame index (e.g. S1-FRAME-1, Frame_046, Frame_103),
    falling back to natural sorting of filename."""
    m = re.search(r'(?:frame[-_]|frame_)(\d+)', p.name, re.I)
    if m:
        return (0, int(m.group(1)), natural_sort_key(p.name))
    return (1, 0, natural_sort_key(p.name))

def discover_images(story_dir: Path) -> List[Path]:
    """Finds all valid images in story_dir (and any subdirectories like images/)."""
    candidates = []
    story_dir = Path(story_dir)
    if not story_dir.exists():
        return []

    for root, _, files in os.walk(story_dir):
        for f in files:
            p = Path(root) / f
            parts_lower = [part.lower() for part in p.parts]
            if any(ref in parts_lower for ref in ["references", "reference", "ref", "refs"]):
                continue
            if p.suffix.lower() in SUPPORTED_EXTENSIONS:
                candidates.append(p)

    unique_candidates = sorted(list(set(candidates)), key=frame_sort_key)
    return unique_candidates

def find_story_script(story_dir: Path) -> Optional[str]:
    """Looks for script.txt or any .txt/.md script file inside the story folder."""
    story_dir = Path(story_dir)
    primary = story_dir / "script.txt"
    if primary.exists():
        with open(primary, "r", encoding="utf-8") as f:
            return f.read()

    # Search for other .txt or .md files
    for f in story_dir.iterdir():
        if f.is_file() and f.suffix.lower() in (".txt", ".md"):
            with open(f, "r", encoding="utf-8") as file_handle:
                return file_handle.read()

    return None

def calculate_image_durations(
    num_images: int,
    total_audio_duration: float,
    transition_duration: float = 0.40
) -> List[float]:
    """Calculates duration per raw clip so that after all transition overlaps,
    the total video duration exactly equals the total audio duration.
    """
    if num_images <= 0:
        return []
    if num_images == 1:
        return [total_audio_duration]

    total_overlap_lost = (num_images - 1) * transition_duration
    total_needed_raw = total_audio_duration + total_overlap_lost
    base_clip_dur = total_needed_raw / num_images

    durations = [round(base_clip_dur, 3)] * num_images
    diff = total_needed_raw - sum(durations)
    durations[-1] = round(durations[-1] + diff, 3)
    return durations

def cleanup_dir(dir_path: Path):
    """Safely cleans up intermediate temporary work files."""
    dir_path = Path(dir_path)
    if dir_path.exists():
        try:
            shutil.rmtree(dir_path)
        except Exception as e:
            logger.warning(f"Could not remove dir {dir_path}: {e}")
