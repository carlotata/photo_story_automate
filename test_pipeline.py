"""End-to-end integration and smoke test for Photo Story Narrator with clean folder structure."""

import os
import sys
import shutil
import logging
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

# Safe UTF-8 console output for Windows cmd / powershell
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import StoryConfig
from src.video_assembler import VideoAssembler
from src.utils import cleanup_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_pipeline")

def create_sample_story(story_dir: Path, count: int = 3):
    story_dir.mkdir(parents=True, exist_ok=True)
    palettes = [
        ((25, 42, 86), (232, 65, 24), "CHAMBER OF SECRETS"),
        ((47, 53, 66), (255, 165, 2), "THE GOLDEN PATH"),
        ((30, 144, 255), (255, 71, 87), "ANCIENT AWAKENING"),
    ]

    for i in range(count):
        img_p = story_dir / f"photo_{i+1:02d}.jpg"
        bg_col, acc_col, title = palettes[i % len(palettes)]
        img = Image.new("RGB", (1080, 1920), bg_col)
        draw = ImageDraw.Draw(img)

        for r in range(120, 600, 90):
            draw.ellipse((540 - r, 960 - r, 540 + r, 960 + r), outline=acc_col, width=5)

        draw.rectangle((100, 850, 980, 1070), fill=(10, 10, 15))
        draw.rectangle((100, 850, 980, 1070), outline=acc_col, width=4)
        draw.text((540, 960), f"SCENE {i+1}: {title}", fill=(255, 255, 255), anchor="mm")
        img.save(img_p, quality=95)

    # Write script.txt inside story folder
    script_p = story_dir / "script.txt"
    script_p.write_text(
        "Deep within the lost temple, ancient walls begin to awaken.\n"
        "Every photograph uncovers secrets hidden for thousands of years.\n"
        "Watch closely as the final mystery is revealed.",
        encoding="utf-8"
    )

def run_test():
    logger.info("Starting Photo Story Narrator Clean Folder Test...")
    cfg = StoryConfig()
    story_title = "The Lost Temple"
    story_dir = cfg.input_dir / story_title

    # 1. Create test story in input/<story_title>/
    create_sample_story(story_dir, count=3)
    logger.info(f"Created sample story in '{story_dir}'")

    # 2. Assemble story video
    assembler = VideoAssembler(cfg)
    output_mp4 = assembler.build_story(story_dir, export_capcut=True)

    # 3. Assertions
    assert output_mp4.exists(), f"Output MP4 missing at: {output_mp4}"
    assert output_mp4.parent.name == story_title, f"Output parent folder should be '{story_title}', got '{output_mp4.parent.name}'"
    assert output_mp4.name == f"{story_title}.mp4", f"Output MP4 filename should be '{story_title}.mp4'"

    # Verify output directory is clean (contains ONLY the mp4)
    output_files = [f.name for f in output_mp4.parent.iterdir()]
    assert output_files == [f"{story_title}.mp4"], f"Output directory contains extra files: {output_files}"

    # Verify duration and streams with ffprobe
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=codec_type",
        "-of", "json",
        str(output_mp4)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"ffprobe error: {res.stderr}"
    logger.info(f"ffprobe duration check: {res.stdout.strip()}")

    # Clean up test files from input and output to leave everything clean
    cleanup_dir(story_dir)
    cleanup_dir(output_mp4.parent)
    cleanup_dir(cfg.work_dir)

    print("\n" + "=" * 60)
    print("✅ TEST PASSED: Clean input/output story folder structure verified!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    run_test()
