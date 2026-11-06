"""Utility helpers for image discovery, story detection, natural sorting, and duration calculations."""

import re
import os
import shutil
import zipfile
import logging
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger("photo_story_narrator.utils")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

def sanitize_title(title: str) -> str:
    """Removes invalid filename characters from story title."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", title).strip()
    return cleaned if cleaned else "Untitled_Story"

def get_story_status(story_dir: Path, output_root: Optional[Path] = None) -> str:
    """Identifies whether a story is 'completed' or 'pending'.
    A story is 'completed' if:
      1. It is inside a 'completed' folder, OR
      2. Its final rendered .mp4 exists in output/<shorts|long>/<StoryTitle>/
    Otherwise, it is 'pending'.
    """
    story_dir = Path(story_dir)
    if "completed" in [p.lower() for p in story_dir.parts]:
        return "completed"

    if output_root is None:
        output_root = PROJECT_ROOT / "output"

    parts_lower = [p.lower() for p in story_dir.parts]
    cat = "shorts" if ("shorts" in parts_lower or "short" in parts_lower) else "long"
    clean_title = sanitize_title(story_dir.name)
    out_dir = output_root / cat / clean_title
    if out_dir.exists():
        mp4s = [p for p in out_dir.glob("*.mp4") if p.stat().st_size > 1000]
        if mp4s:
            return "completed"

    return "pending"

def move_story_to_completed(story_dir: Path, completed_dir: Path) -> Path:
    """Moves a finished story folder into completed/ without data loss."""
    story_dir = Path(story_dir)
    completed_dir = Path(completed_dir)
    completed_dir.mkdir(parents=True, exist_ok=True)
    dest = completed_dir / story_dir.name
    if story_dir.resolve() == dest.resolve():
        return dest
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(story_dir), str(dest))
    return dest

def auto_organize_story_folders(input_root: Path, output_root: Optional[Path] = None):
    """Automatically identifies story completion and organizes input folders:
    - Moves completed stories (with rendered .mp4 in output) into completed/
    - Moves unrendered stories sitting in category root into pending/
    """
    input_root = Path(input_root)
    if output_root is None:
        output_root = PROJECT_ROOT / "output"
    if not input_root.exists():
        return

    for cat in ["shorts", "long"]:
        cat_dir = input_root / cat
        if not cat_dir.exists():
            continue
        pending_dir = cat_dir / "pending"
        completed_dir = cat_dir / "completed"
        pending_dir.mkdir(parents=True, exist_ok=True)
        completed_dir.mkdir(parents=True, exist_ok=True)

        for item in list(cat_dir.iterdir()):
            if not item.is_dir() or item.name.startswith("."):
                continue
            if item.name.lower() in ("pending", "completed"):
                # Check if any story inside pending is actually completed
                if item.name.lower() == "pending":
                    for p_item in list(item.iterdir()):
                        if p_item.is_dir() and not p_item.name.startswith("."):
                            if get_story_status(p_item, output_root) == "completed":
                                move_story_to_completed(p_item, completed_dir)
                continue

            # Story is sitting in category root
            status = get_story_status(item, output_root)
            if status == "completed":
                move_story_to_completed(item, completed_dir)
            else:
                dest = pending_dir / item.name
                if dest != item:
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.move(str(item), str(dest))

def auto_extract_zips(directory: Path):
    """Detects .zip archives in directory, automatically unpacks them into story folders,
    and removes the archive once unpacked."""
    directory = Path(directory)
    if not directory.exists() or not directory.is_dir():
        return

    for zip_path in list(directory.glob("*.zip")):
        try:
            logger.info(f"Detected archive: {zip_path.name}. Auto-extracting...")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Check whether zip has a single root folder or flat files
                namelist = [p for p in zf.namelist() if p.strip()]
                top_levels = {p.split('/')[0].split('\\')[0] for p in namelist}
                
                # If zip contains a single top-level folder, extract directly to directory
                if len(top_levels) == 1 and not any(f.lower().endswith(tuple(SUPPORTED_EXTENSIONS)) for f in top_levels):
                    extract_target = directory
                else:
                    # Check if there is an existing folder matching this episode prefix
                    matching_dirs = [d for d in directory.iterdir() if d.is_dir() and d.name.lower().startswith(zip_path.stem.lower())]
                    if matching_dirs:
                        extract_target = matching_dirs[0]
                    else:
                        extract_target = directory / zip_path.stem

                extract_target.mkdir(parents=True, exist_ok=True)
                zf.extractall(extract_target)
                logger.info(f"Successfully unpacked {zip_path.name} to {extract_target}")

            try:
                zip_path.unlink()
            except Exception as e:
                logger.warning(f"Could not remove {zip_path} after extraction: {e}")
        except Exception as e:
            logger.error(f"Failed to auto-extract {zip_path}: {e}")

def natural_sort_key(s: str):
    """Sort strings containing numbers in human order (e.g., img2 before img10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", str(s))]

def discover_stories(input_root: Path, category: Optional[str] = None) -> List[Path]:
    """Finds all story subdirectories inside input/ (including categorized subfolders input/shorts and input/long,
    as well as pending/ and completed/ subfolders)."""
    input_root = Path(input_root)
    if not input_root.exists():
        return []

    # Auto-organize input stories based on completion status
    auto_organize_story_folders(input_root)

    # Auto-extract any zip files in input_root and subdirectories
    for d in [
        input_root,
        input_root / "shorts",
        input_root / "shorts" / "pending",
        input_root / "shorts" / "completed",
        input_root / "long",
        input_root / "long" / "pending",
        input_root / "long" / "completed",
    ]:
        if d.exists():
            auto_extract_zips(d)

    def scan_container(container_dir: Path) -> List[Path]:
        found = []
        if not container_dir.exists() or not container_dir.is_dir():
            return found
        for item in sorted(container_dir.iterdir()):
            if not item.is_dir() or item.name.startswith("."):
                continue
            # If item is a workflow container like 'pending' or 'completed', inspect child story folders
            if item.name.lower() in ("pending", "completed"):
                for sub_item in sorted(item.iterdir()):
                    if sub_item.is_dir() and not sub_item.name.startswith("."):
                        if discover_images(sub_item):
                            found.append(sub_item)
            else:
                # Direct story folder
                if discover_images(item):
                    found.append(item)
        return found

    stories = []

    # Category filter
    if category in ("shorts", "short"):
        shorts_dir = input_root / "shorts" if input_root.name.lower() != "shorts" else input_root
        return scan_container(shorts_dir)

    if category in ("long", "longs"):
        long_dir = input_root / "long" if input_root.name.lower() != "long" else input_root
        return scan_container(long_dir)

    # If no category specified, check categorized folders first:
    for cat_name in ["shorts", "long"]:
        cat_dir = input_root / cat_name
        stories.extend(scan_container(cat_dir))

    # Then check any top-level story folders in input_root (excluding 'shorts' & 'long')
    for item in sorted(input_root.iterdir()):
        if item.is_dir() and not item.name.startswith(".") and item.name.lower() not in ("shorts", "short", "long", "longs"):
            if item.name.lower() in ("pending", "completed"):
                for sub_item in sorted(item.iterdir()):
                    if sub_item.is_dir() and not sub_item.name.startswith(".") and discover_images(sub_item):
                        stories.append(sub_item)
            elif discover_images(item):
                stories.append(item)

    # Return unique paths preserving discovery order
    seen = set()
    unique_stories = []
    for s in stories:
        if s not in seen:
            seen.add(s)
            unique_stories.append(s)
    return unique_stories

def frame_sort_key(p: Path):
    """Sorts images by explicit frame index (e.g. S1-FRAME-1, Frame_046, E02_F001, Frame_103),
    falling back to natural sorting of filename."""
    m = re.search(r'(?:e\d+[-_])?(?:frame[-_]|frame_|f)(\d+)', p.name, re.I)
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
            if any(term in p.name.lower() for term in ["thumb", "thumbnail"]):
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
