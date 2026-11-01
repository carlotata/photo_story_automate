#!/usr/bin/env python3
"""CLI runner for Photo Story Narrator.

Clean workflow:
  input/<StoryTitle>/    -> Place images and script.txt here
  output/<StoryTitle>/   -> Contains ONLY <StoryTitle>.mp4
"""

import sys
import argparse
import logging
from pathlib import Path

# Safe UTF-8 console output for Windows cmd / powershell
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import StoryConfig, VideoConfig, VoiceConfig, SubtitleConfig, KenBurnsConfig, TransitionConfig
from src.video_assembler import VideoAssembler
from src.utils import discover_stories

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("run")

def parse_args():
    parser = argparse.ArgumentParser(description="Render photo slideshow with deep male Kokoro narration and synced subtitles.")
    parser.add_argument("story", nargs="?", default=None, help="Name of the story folder inside input/ (e.g. 'The Ancient Temple').")
    parser.add_argument("--script", "-s", type=str, default=None, help="Optional script override text or path to script file.")
    parser.add_argument("--voice", "-v", type=int, default=5, choices=list(range(11)),
                        help="Kokoro voice ID: 5 (am_adam - Conversational Male, Default), 6 (am_michael - Deep Documentary), 9 (bm_george - Deep British), 1 (af_bella - Expressive Female), 0-10 available.")
    parser.add_argument("--aspect", "-a", type=str, default="auto", choices=["auto", "9:16", "16:9", "1:1"],
                        help="Aspect ratio: auto (detects from images), 9:16 (Shorts/Reels), 16:9 (Widescreen), 1:1 (Square).")
    parser.add_argument("--transition", "-t", type=str, default="random_cinematic",
                        choices=["random_cinematic", "cut", "blur", "dissolve", "zoomin", "slideleft"],
                        help="Transition style between images.")
    parser.add_argument("--no-capcut", action="store_true", help="Disable automatic CapCut draft project export.")
    parser.add_argument("--all", action="store_true", help="Render all story folders found inside input/.")
    return parser.parse_args()

def main():
    args = parse_args()
    cfg = StoryConfig()

    # Configure aspect ratio helper
    def apply_aspect(aspect_choice: str, sample_img: Path = None):
        if aspect_choice == "auto" and sample_img and sample_img.exists():
            try:
                from PIL import Image
                with Image.open(sample_img) as im:
                    w, h = im.size
                aspect_choice = "16:9" if w > h else ("9:16" if h > w else "1:1")
                logger.info(f"Auto-detected aspect ratio: {aspect_choice} from image {sample_img.name} ({w}x{h})")
            except Exception:
                aspect_choice = "16:9"

        if aspect_choice == "16:9":
            cfg.video.width = 2560
            cfg.video.height = 1440
            cfg.subtitle.margin_v = 150
            cfg.subtitle.font_size = 72
            cfg.subtitle.outline_width = 4.8
        elif aspect_choice == "1:1":
            cfg.video.width = 1440
            cfg.video.height = 1440
            cfg.subtitle.margin_v = 130
            cfg.subtitle.font_size = 64
            cfg.subtitle.outline_width = 4.8
        else: # 9:16
            cfg.video.width = 1440
            cfg.video.height = 2560
            cfg.subtitle.margin_v = 180
            cfg.subtitle.font_size = 64
            cfg.subtitle.outline_width = 4.8

    # Configure voice
    cfg.voice.speaker_id = args.voice
    voice_names = {
        0: "af_alloy (American Female)",
        1: "af_bella (American Female - Expressive)",
        2: "af_heart (American Female - Calm)",
        3: "af_nicole (American Female - Gentle)",
        4: "af_sarah (American Female - Confident)",
        5: "am_adam (American Male - Conversational Default)",
        6: "am_michael (American Male - Deep Documentary)",
        7: "bf_emma (British Female - Articulate)",
        8: "bf_isabella (British Female - Melodic)",
        9: "bm_george (British Male - Resonant Historical)",
        10: "bm_lewis (British Male - Smooth & Composed)"
    }
    cfg.voice.speaker_name = voice_names.get(args.voice, "am_adam")

    # Configure transition
    cfg.transition.default_transition = args.transition

    # Discover target story folders
    all_stories = discover_stories(cfg.input_dir)
    target_stories = []

    if args.story:
        # Check explicit story name or path
        candidate = cfg.input_dir / args.story
        if candidate.exists() and candidate.is_dir():
            target_stories.append(candidate)
        elif Path(args.story).exists() and Path(args.story).is_dir():
            target_stories.append(Path(args.story))
        else:
            logger.error(f"Story folder not found: '{args.story}' inside '{cfg.input_dir}'")
            sys.exit(1)
    elif args.all:
        target_stories = all_stories
    elif len(all_stories) == 1:
        target_stories = all_stories
    elif len(all_stories) > 1:
        print("\nMultiple stories found in input/:")
        for i, s in enumerate(all_stories, 1):
            print(f"  {i}. {s.name}")
        print("\nSpecify which story to render: python run.py \"StoryName\" or python run.py --all\n")
        sys.exit(0)
    else:
        # Check if user put images directly inside input/
        from src.utils import discover_images
        loose_images = discover_images(cfg.input_dir)
        if loose_images:
            # Wrap into a default story folder
            default_dir = cfg.input_dir / "Default_Story"
            default_dir.mkdir(parents=True, exist_ok=True)
            for img in loose_images:
                if img.parent == cfg.input_dir:
                    import shutil
                    shutil.move(str(img), str(default_dir / img.name))
            target_stories.append(default_dir)
        else:
            print("\n[!] No story folders or images found in 'input/'.")
            print("Create a story folder:  input/<Your Story Title>/")
            print("and place your images (and optional script.txt) inside it.\n")
            sys.exit(1)

    # Optional script text override
    script_text = None
    if args.script:
        if Path(args.script).exists() and Path(args.script).is_file():
            with open(args.script, "r", encoding="utf-8") as f:
                script_text = f.read()
        else:
            script_text = args.script

    rendered_videos = []

    for s_dir in target_stories:
        try:
            # Auto-detect aspect ratio per story if set to auto
            from src.utils import discover_images
            story_imgs = discover_images(s_dir)
            first_img = story_imgs[0] if story_imgs else None
            apply_aspect(args.aspect, first_img)

            assembler = VideoAssembler(cfg)
            out_file = assembler.build_story(
                story_dir=s_dir,
                script_text=script_text,
                export_capcut=False
            )
            rendered_videos.append(out_file)
        except Exception as e:
            logger.error(f"Failed to render '{s_dir.name}': {e}", exc_info=True)

    print("\n" + "=" * 60)
    print(f"🎉 RENDER SUMMARY: {len(rendered_videos)} story video(s) created:")
    for v in rendered_videos:
        print(f"   🎬 {v.parent.name}: {v}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
