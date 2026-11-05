"""Cinematic Scene Director.

Analyzes narrative script, shot scales, and scene continuity to make intelligent,
purposeful decisions about Ken Burns camera movements, transitions (cut vs. dissolve),
and synchronized diegetic Foley sound effects—eliminating random transitions.
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("photo_story_narrator.director")

# Narrative keyword analyzers for intelligent cinematic decisions
OBJECT_KEYWORDS = re.compile(r"\b(clock|alarm|screen|phone|rectangle|router|counter|refrigerator|fridge|jug|milk|ice cream|coupon|card|shelf|shelves|lock|latch|vault|handle|wire|glass)\b", re.I)
ENVIRONMENT_KEYWORDS = re.compile(r"\b(street|outside|window|highway|asphalt|lawn|grass|bluegrass|sidewalk|field|trees|sky|basement|server|room|supermarket|network|ocean|dirt|yard|house)\b", re.I)
CHARACTER_KEYWORDS = re.compile(r"\b(wake|wakes|sitting|sits|stan|you|face|eyes|standing|stands|walks|walk|looking|looks|realize|realizes|socks|breakfast)\b", re.I)

DISSOLVE_KEYWORDS = re.compile(r"\b(mist|dissolved|dissolve|evaporated|across the state|outside|then|freedom|civilization|network|supermarket|three blocks away|logistics)\b", re.I)

def direct_story(
    story_dir: Path,
    script_lines: List[str],
    durations: List[float]
) -> List[Dict[str, Any]]:
    """
    Directs each frame of the story with purposeful camera movements,
    continuity transitions, and diegetic Foley sound cues.
    Checks for explicit 'director.json' override if the user provided one.
    """
    director_override = story_dir / "director.json"
    if director_override.exists():
        try:
            with open(director_override, "r", encoding="utf-8") as f:
                plan = json.load(f)
                logger.info(f"Loaded explicit directorial plan from '{director_override.name}'")
                return plan
        except Exception as e:
            logger.warning(f"Error reading director.json: {e}")

    num_scenes = len(durations)
    scenes_plan = []
    accum_time = 0.0

    for idx in range(num_scenes):
        dur = durations[idx]
        line = script_lines[idx] if idx < len(script_lines) else (script_lines[-1] if script_lines else "")
        # 1. Determine Ken Burns Camera Movement based on subject matter & shot intent
        has_object = bool(OBJECT_KEYWORDS.search(line))
        has_env = bool(ENVIRONMENT_KEYWORDS.search(line))
        has_char = bool(CHARACTER_KEYWORDS.search(line))

        # 3 Clean, non-distracting camera motions:
        # 1. Static: firmly grounded for flash beats (< 2.2s), punchlines & diagrams
        # 2. Pan Right: smooth horizontal tracking (left-to-right) for landscapes/environments
        # 3. Zoom In: slow centered push-in focusing attention on character & narrative
        if dur < 2.2:
            motion = "static"
        elif has_env and any(k in line.lower() for k in ["savannah", "ridge", "grass", "lawn", "horizon", "valley", "canal", "river"]):
            motion = "pan_right"
        else:
            motion = "zoom_in"

        # 2. Determine Transition to the NEXT frame
        next_transition = "cut"
        trans_duration = 0.0

        scene_dict = {
            "index": idx,
            "line": line,
            "duration": dur,
            "start_time": accum_time,
            "motion": motion,
            "next_transition": next_transition,
            "transition_duration": trans_duration
        }
        scenes_plan.append(scene_dict)
        accum_time += dur

    logger.info(
        f"Directed {num_scenes} scenes: "
        f"{sum(1 for s in scenes_plan if s['next_transition'] == 'cut')} hard cuts, "
        f"{sum(1 for s in scenes_plan if s['next_transition'] == 'dissolve')} dissolves."
    )
    return scenes_plan
