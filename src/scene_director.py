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

    num_scenes = len(script_lines)
    scenes_plan = []
    accum_time = 0.0

    for idx, (line, dur) in enumerate(zip(script_lines, durations)):
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
        # For animated 2D rage-comic explainer videos, all scene edits are clean,
        # instantaneous hard cuts locked to the acoustic sentence boundaries.
        next_transition = "cut"
        trans_duration = 0.0

        # 3. Detect Diegetic Foley Sound Cues from the script narrative
        foley_cues = []
        l_lower = line.lower()

        # Specific diegetic narrative sound triggers
        if "buzzing alarm" in l_lower or "alarm clock" in l_lower:
            foley_cues.append({"name": "buzzing_alarm", "offset": 0.3, "gain": 0.38})
        elif "mechanical bell" in l_lower or "bell strikes" in l_lower:
            foley_cues.append({"name": "alarm_bell", "offset": 0.8, "gain": 0.40})
        elif "digital bank account" in l_lower or "currency appears" in l_lower:
            foley_cues.append({"name": "notification_ping", "offset": 1.0, "gain": 0.35})
        elif "marked pebbles" in l_lower or "gambling with" in l_lower:
            foley_cues.append({"name": "pebble_clatter", "offset": 0.6, "gain": 0.40})
        elif "open hearth" in l_lower or "telling stories around" in l_lower or "hearth embers" in l_lower:
            foley_cues.append({"name": "campfire", "offset": 0.2, "gain": 0.35})
        elif "broken spear" in l_lower or "spear tip" in l_lower or "bronze spears" in l_lower:
            foley_cues.append({"name": "spear_snap", "offset": 0.6, "gain": 0.38})
        elif "rot in the rain" in l_lower or "rain" in l_lower or "drip" in l_lower or "melts" in l_lower:
            foley_cues.append({"name": "water_drip", "offset": 0.8, "gain": 0.40})
        elif "reed styluses" in l_lower or "invent writing" in l_lower or "cuneiform" in l_lower:
            foley_cues.append({"name": "screen_tap", "offset": 0.5, "gain": 0.35})
        elif "sour beer" in l_lower or "beer issued" in l_lower:
            foley_cues.append({"name": "pebble_clatter", "offset": 0.4, "gain": 0.32})
        elif "workload explodes" in l_lower or "surplus demands" in l_lower:
            foley_cues.append({"name": "cinematic_thump", "offset": 0.3, "gain": 0.42})
        elif "vault door" in l_lower or "unlatched vault" in l_lower:
            foley_cues.append({"name": "vault_latch", "offset": 0.8, "gain": 0.55})
        elif "breeze pushes open the front door" in l_lower or "front door" in l_lower:
            foley_cues.append({"name": "door_creak", "offset": 0.5, "gain": 0.42})
            foley_cues.append({"name": "wind_breeze", "offset": 1.2, "gain": 0.28})
        elif "digital alarm does not chime" in l_lower or "electrical grid died" in l_lower:
            foley_cues.append({"name": "power_down", "offset": 0.6, "gain": 0.38})
        elif "slab of glass" in l_lower or "phone" in l_lower:
            foley_cues.append({"name": "screen_tap", "offset": 1.0, "gain": 0.30})
        elif "front yard in your socks" in l_lower or "wet morning soil" in l_lower:
            foley_cues.append({"name": "grass_squish", "offset": 1.4, "gain": 0.45})
            foley_cues.append({"name": "cinematic_thump", "offset": 3.2, "gain": 0.40})
        elif "street sits entirely silent" in l_lower or "outside the bedroom window" in l_lower:
            foley_cues.append({"name": "wind_breeze", "offset": 0.4, "gain": 0.25})
        elif "air conditioning unit" in l_lower:
            foley_cues.append({"name": "metal_ping", "offset": 1.2, "gain": 0.28})
        elif "bank server" in l_lower:
            foley_cues.append({"name": "server_winddown", "offset": 0.8, "gain": 0.32})
        elif "lawnmower sits abandoned" in l_lower or "kentucky bluegrass" in l_lower or "savannah" in l_lower:
            foley_cues.append({"name": "wind_breeze", "offset": 0.6, "gain": 0.22})
        elif "does not exist" in l_lower or "tuesday does not" in l_lower or "toxic mushrooms" in l_lower:
            foley_cues.append({"name": "cinematic_thump", "offset": 0.6, "gain": 0.42})
        elif idx == 0:
            # Opening scene hook: gentle room dawn tone & soft subtle opening hit
            foley_cues.append({"name": "cinematic_thump", "offset": 0.0, "gain": 0.45})

        scene_dict = {
            "index": idx,
            "line": line,
            "duration": dur,
            "start_time": accum_time,
            "motion": motion,
            "next_transition": next_transition,
            "transition_duration": trans_duration,
            "foley_cues": foley_cues
        }
        scenes_plan.append(scene_dict)
        accum_time += dur

    logger.info(
        f"Directed {num_scenes} scenes: "
        f"{sum(1 for s in scenes_plan if s['next_transition'] == 'cut')} hard cuts, "
        f"{sum(1 for s in scenes_plan if s['next_transition'] == 'dissolve')} dissolves, "
        f"{sum(len(s['foley_cues']) for s in scenes_plan)} diegetic Foley sound cues."
    )
    return scenes_plan
