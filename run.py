#!/usr/bin/env python3
"""CLI runner for Photo Story Narrator.

Categorized Workflow:
  Short Form (9:16, <= 59s maximum):
    input/shorts/<StoryTitle>/    -> Place images and script.txt here
    output/shorts/<StoryTitle>/   -> Contains ONLY <StoryTitle>.mp4
    Command: python run.py /shorts [StoryTitle]  or  /shorts

  Long Form (16:9 2K Widescreen default):
    input/long/<StoryTitle>/      -> Place images and script.txt here
    output/long/<StoryTitle>/     -> Contains ONLY <StoryTitle>.mp4
    Command: python run.py /long [StoryTitle]  or  /long
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
    # Preprocess slash commands or shortcut keywords in sys.argv:
    # Handles: python run.py /shorts [Story], python run.py /long [Story], etc.
    raw_args = sys.argv[1:]
    format_override = None
    story_override = None

    filtered_args = []
    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        lower_arg = arg.lower()
        if lower_arg in ("/photoshorts", "photoshorts", "/shorts", "shorts", "--shorts"):
            format_override = "shorts"
            if i + 1 < len(raw_args) and not raw_args[i + 1].startswith("-") and not raw_args[i + 1].startswith("/"):
                story_override = raw_args[i + 1]
                i += 1
        elif lower_arg in ("/photolong", "photolong", "/long", "long", "--long"):
            format_override = "long"
            if i + 1 < len(raw_args) and not raw_args[i + 1].startswith("-") and not raw_args[i + 1].startswith("/"):
                story_override = raw_args[i + 1]
                i += 1
        else:
            filtered_args.append(arg)
        i += 1

    parser = argparse.ArgumentParser(description="Photo Story Narrator: Automated video production for Short Form (9:16, <=59s) and Long Form (16:9 2K).")
    parser.add_argument("story", nargs="?", default=story_override, help="Name of the story folder inside input/shorts/ or input/long/.")
    parser.add_argument("--format", "-f", choices=["auto", "shorts", "long"], default=format_override or "auto",
                        help="Content category: 'shorts' (9:16, <=59s max), 'long' (16:9 widescreen 2K), or 'auto'.")
    parser.add_argument("--script", "-s", type=str, default=None, help="Optional script override text or path to script file.")
    parser.add_argument("--voice", "-v", type=int, default=None, choices=list(range(11)),
                        help="Kokoro voice ID: 6 (am_michael - Deep Documentary Narrator, Long default), 5 (am_adam - Conversational Male, Shorts default), 0-10 available.")
    parser.add_argument("--aspect", "-a", type=str, default="auto", choices=["auto", "9:16", "16:9", "1:1"],
                        help="Aspect ratio: auto (detects from category/images), 9:16 (Shorts), 16:9 (Long Widescreen), 1:1 (Square).")
    parser.add_argument("--transition", "-t", type=str, default="random_cinematic",
                        choices=["random_cinematic", "cut", "blur", "dissolve", "zoomin", "slideleft"],
                        help="Transition style between images.")
    parser.add_argument("--workers", "-w", type=int, default=4,
                        help="Number of parallel render workers for Ken Burns clips (default: 4).")
    parser.add_argument("--no-capcut", action="store_true", help="Disable automatic CapCut draft project export.")
    parser.add_argument("--all", action="store_true", help="Render all story folders found inside target category.")
    
    parsed = parser.parse_args(filtered_args)
    if format_override and parsed.format == "auto":
        parsed.format = format_override
    if story_override and not parsed.story:
        parsed.story = story_override
    return parsed

def main():
    args = parse_args()
    cfg = StoryConfig()
    cfg.content_format = args.format

    # Set default voice (am_michael ID 6 used across both shorts and long by default)
    if args.voice is None:
        args.voice = 6  # am_michael: deep cinematic documentary narrator

    # Configure aspect ratio helper
    def apply_aspect(aspect_choice: str, is_short_category: bool, sample_img: Path = None):
        if aspect_choice == "auto":
            if is_short_category:
                aspect_choice = "9:16"
            elif sample_img and sample_img.exists():
                try:
                    from PIL import Image
                    with Image.open(sample_img) as im:
                        w, h = im.size
                    aspect_choice = "9:16" if h > w else "16:9"
                    logger.info(f"Auto-detected aspect ratio: {aspect_choice} from image {sample_img.name} ({w}x{h})")
                except Exception:
                    aspect_choice = "16:9"
            else:
                aspect_choice = "16:9"

        if aspect_choice == "9:16":
            cfg.video.width = 1440
            cfg.video.height = 2560
            cfg.subtitle.margin_v = 240
            cfg.subtitle.font_size = 68
            cfg.subtitle.words_per_group = 3
            cfg.subtitle.outline_width = 4.8
        elif aspect_choice == "1:1":
            cfg.video.width = 1440
            cfg.video.height = 1440
            cfg.subtitle.margin_v = 130
            cfg.subtitle.font_size = 64
            cfg.subtitle.outline_width = 4.8
        else: # 16:9 Widescreen
            cfg.video.width = 2560
            cfg.video.height = 1440
            cfg.subtitle.margin_v = 150
            cfg.subtitle.font_size = 72
            cfg.subtitle.words_per_group = 3
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
    cfg.voice.speaker_name = voice_names.get(args.voice, "am_michael")

    # Configure transition & workers
    cfg.transition.default_transition = args.transition
    cfg.render_workers = max(1, args.workers)

    # Ensure categorized folder structure exists
    cfg.input_shorts_dir.mkdir(parents=True, exist_ok=True)
    cfg.input_long_dir.mkdir(parents=True, exist_ok=True)
    cfg.output_shorts_dir.mkdir(parents=True, exist_ok=True)
    cfg.output_long_dir.mkdir(parents=True, exist_ok=True)

    # Discover target story folders based on category
    category_filter = None if args.format == "auto" else args.format
    all_stories = discover_stories(cfg.input_dir, category=category_filter)
    target_stories = []

    if args.story:
        # Check explicit story name across categorized paths
        candidates = [
            cfg.input_shorts_dir / args.story,
            cfg.input_long_dir / args.story,
            cfg.input_dir / args.story,
            Path(args.story)
        ]
        found = None
        for cand in candidates:
            if cand.exists() and cand.is_dir():
                found = cand
                break
        
        # Fuzzy match across discovered stories if exact path wasn't found
        if not found:
            def norm_key(text: str) -> str:
                import re
                return re.sub(r'[^a-z0-9]', '', text.lower())
            
            target_key = norm_key(args.story)
            for s in all_stories:
                s_key = norm_key(s.name)
                if target_key == s_key or target_key in s_key or s_key in target_key:
                    found = s
                    break

        if found:
            target_stories.append(found)
        else:
            logger.error(f"Story folder not found: '{args.story}' in input/shorts/ or input/long/")
            sys.exit(1)
    elif args.all:
        target_stories = all_stories
    elif len(all_stories) == 1:
        target_stories = all_stories
    elif len(all_stories) > 1:
        print("\nAvailable stories:")
        shorts_list = [s for s in all_stories if "shorts" in [p.lower() for p in s.parts]]
        long_list = [s for s in all_stories if "long" in [p.lower() for p in s.parts]]
        other_list = [s for s in all_stories if s not in shorts_list and s not in long_list]

        if shorts_list:
            print("\n  📱 SHORT FORM (input/shorts/):")
            for i, s in enumerate(shorts_list, 1):
                print(f"     {i}. {s.name}")
        if long_list:
            print("\n  🎬 LONG FORM (input/long/):")
            for i, s in enumerate(long_list, 1):
                print(f"     {i}. {s.name}")
        if other_list:
            print("\n  📁 UNCATEGORIZED (input/):")
            for i, s in enumerate(other_list, 1):
                print(f"     {i}. {s.name}")

        print("\nSpecify story to render:")
        print("   Shorts: python run.py /photoshorts \"StoryName\"  or  /photoshorts")
        print("   Long:   python run.py /photolong \"StoryName\"    or  /photolong")
        print("   All:    python run.py --all\n")
        sys.exit(0)
    else:
        print("\n[!] No story folders found in 'input/shorts/' or 'input/long/'.")
        print("Place your story folder inside:")
        print("   - input/shorts/<Story Title>/ (for 9:16 short form, <=59s)")
        print("   - input/long/<Story Title>/   (for 16:9 long form 2K)\n")
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
            from src.utils import discover_images
            story_imgs = discover_images(s_dir)
            first_img = story_imgs[0] if story_imgs else None
            is_short = (args.format == "shorts") or ("shorts" in [p.lower() for p in s_dir.parts])
            apply_aspect(args.aspect, is_short, first_img)

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
        cat = "📱 SHORT FORM" if "shorts" in [p.lower() for p in v.parts] else "🎬 LONG FORM"
        print(f"   [{cat}] {v.parent.name}: {v}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
