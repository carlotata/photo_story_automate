"""Master Video Assembler coordinating TTS, scene-directed Ken Burns,
purposeful transitions (cuts vs dissolves), natural Foley sound effects, and subtitles."""

import os
import shutil
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .config import StoryConfig
from .tts_engine import TTSEngine, clean_script_text
from .ken_burns import render_image_clip
from .transitions import stitch_batch_xfade, stitch_clips_cut
from .subtitle_gen import SubtitleGenerator
from .scene_director import direct_story
from .sfx_engine import build_natural_soundtrack
from .audio_aligner import align_narration_audio
from .utils import discover_images, find_story_script, calculate_image_durations, sanitize_title, cleanup_dir
from .capcut_exporter import export_to_capcut_draft

logger = logging.getLogger("photo_story_narrator.assembler")

def escape_ffmpeg_path(path: Path) -> str:
    """Escapes Windows path for FFmpeg filters."""
    p_str = str(path.resolve()).replace("\\", "/")
    if len(p_str) > 1 and p_str[1] == ":":
        p_str = p_str[0] + "\\:" + p_str[2:]
    return p_str

class VideoAssembler:
    def __init__(self, config: StoryConfig):
        self.cfg = config
        self.tts = TTSEngine(config.voice)
        self.sub_gen = SubtitleGenerator(config.subtitle, config.video)

    def build_story(
        self,
        story_dir: Path,
        script_text: Optional[str] = None,
        export_capcut: bool = False
    ) -> Path:
        """Processes a single story folder from input/<StoryTitle>/ to output/<StoryTitle>/<StoryTitle>.mp4."""
        story_dir = Path(story_dir)
        story_title = sanitize_title(story_dir.name)

        # Clean output folder: output/<StoryTitle>/
        output_story_dir = self.cfg.output_dir / story_title
        output_story_dir.mkdir(parents=True, exist_ok=True)
        final_mp4 = output_story_dir / f"{story_title}.mp4"

        # Dedicated work directory for all temp files
        work_story_dir = self.cfg.work_dir / story_title
        work_story_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"--- Processing Story: '{story_title}' ---")

        # 1. Discover images
        images = discover_images(story_dir)
        if not images:
            raise ValueError(f"No images found inside '{story_dir}'. Please paste photos inside this folder.")

        num_images = len(images)
        logger.info(f"Discovered {num_images} images in '{story_dir.name}'.")

        # 2. Read script
        if not script_text:
            script_text = find_story_script(story_dir)

        if not script_text or not script_text.strip():
            raise ValueError(f"No script found. Please paste script.txt inside '{story_dir}' or pass --script.")

        script_lines = clean_script_text(script_text)

        # 3. Generate Kokoro voiceover
        voice_wav_path = work_story_dir / "voiceover.wav"
        tts_meta = self.tts.generate_narration(script_text, voice_wav_path)
        total_audio_dur = tts_meta["total_duration"]

        # 4. Acoustic Forced Alignment directly from the recorded audio waveform
        alignment_res = align_narration_audio(
            voice_wav_path=voice_wav_path,
            script_lines=script_lines,
            num_frames=num_images,
            tts_segments=tts_meta.get("segments", [])
        )
        aligned_frames = alignment_res["frames"]
        raw_durations = [f["duration"] for f in aligned_frames]

        # 5. Generate Subtitles (.ass) using exact acoustic word timings
        ass_sub_path = work_story_dir / "subtitles.ass"
        acoustic_words = alignment_res.get("words", tts_meta.get("words", []))
        self.sub_gen.generate_ass(acoustic_words, tts_meta.get("segments", []), ass_sub_path)

        # 6. Scene direction based on exact acoustic per-sentence durations
        scenes_plan = direct_story(story_dir, script_lines, raw_durations)

        # Sync scenes_plan start_time and duration with exact acoustic speech bounds
        for i, sc in enumerate(scenes_plan):
            sc["start_time"] = aligned_frames[i]["start_time"]
            sc["speech_start"] = aligned_frames[i]["speech_start"]
            sc["speech_end"] = aligned_frames[i]["speech_end"]
            sc["duration"] = raw_durations[i]

        # Transition plan:
        # Cuts: t_dur = 0.0 (no overlap, clip plays exact acoustic duration)
        # Dissolves: t_dur is added to clip so visual cross-fade overlaps seamlessly
        transition_plan = []
        clip_durations = []
        for i, sc in enumerate(scenes_plan):
            if i < num_images - 1:
                t_name = sc.get("next_transition", "cut")
                t_dur = sc.get("transition_duration", 0.0) if t_name == "dissolve" else 0.0
                transition_plan.append((t_name, t_dur))
                clip_durations.append(raw_durations[i] + t_dur)
            else:
                clip_durations.append(raw_durations[i])

        durations = clip_durations
        logger.info(f"Acoustically pinpointed {num_images} clips to recorded audio waveform (total: {total_audio_dur:.2f}s)")

        # 6. Render Butter-Smooth Scene-Directed Ken Burns Clips
        clip_paths = []
        logger.info(f"Rendering {num_images} scene-directed Ken Burns clips...")

        for idx, (img_path, dur, sc) in enumerate(zip(images, durations, scenes_plan)):
            motion = sc.get("motion", "zoom_in")
            clip_path = work_story_dir / f"clip_{idx:05d}.mp4"
            if not (clip_path.exists() and clip_path.stat().st_size > 1000):
                render_image_clip(
                    image_path=img_path,
                    output_clip_path=clip_path,
                    duration=dur,
                    motion_type=motion,
                    video_config=self.cfg.video,
                    kb_config=self.cfg.ken_burns
                )
            clip_paths.append((clip_path, dur))
            if (idx + 1) % 10 == 0 or (idx + 1) == num_images:
                logger.info(f"Rendered/Verified Ken Burns clips: {idx + 1}/{num_images}")

        # 7. Batch Stitching with Scene Transitions (Purposeful Cuts & Dissolves)
        batch_size = self.cfg.chunk_batch_size
        chunk_mp4s = []
        merged_raw_video = work_story_dir / "stitched_raw.mp4"

        all_cuts = all(t[0] == "cut" or t[1] <= 0.0 for t in transition_plan)
        if all_cuts:
            logger.info(f"All {num_images} transitions are instantaneous acoustic cuts. Stitching directly via concat demuxer...")
            stitch_clips_cut([c[0] for c in clip_paths], merged_raw_video, work_story_dir)
        elif num_images <= batch_size:
            stitch_batch_xfade(
                clips=clip_paths,
                output_path=merged_raw_video,
                trans_config=self.cfg.transition,
                video_config=self.cfg.video,
                transition_plan=transition_plan
            )
        else:
            logger.info(f"Stitching {num_images} clips across batches of {batch_size}...")
            for b_idx in range(0, num_images, batch_size):
                batch_clips = clip_paths[b_idx : b_idx + batch_size]
                batch_trans = transition_plan[b_idx : b_idx + len(batch_clips) - 1]
                chunk_out = work_story_dir / f"chunk_{b_idx // batch_size:03d}.mp4"
                stitch_batch_xfade(
                    clips=batch_clips,
                    output_path=chunk_out,
                    trans_config=self.cfg.transition,
                    video_config=self.cfg.video,
                    transition_plan=batch_trans
                )
                chunk_mp4s.append(chunk_out)

            stitch_clips_cut(chunk_mp4s, merged_raw_video, work_story_dir)

        # 8. Build Natural Foley & Soundtrack Mix
        mix_wav_path = work_story_dir / "natural_soundtrack.wav"
        build_natural_soundtrack(
            voice_wav_path=voice_wav_path,
            output_mix_path=mix_wav_path,
            scenes_plan=scenes_plan,
            foley_master_gain=0.35
        )

        # 9. Final Burn-in & Muxing (Clean Video + Natural Soundtrack + Subtitles)
        # Note: NO TEXT BADGES (completely clean visuals as requested)
        logger.info(f"Final compositing: muxing clean video, subtitles & natural Foley into '{final_mp4.name}'...")
        escaped_sub = escape_ffmpeg_path(ass_sub_path)

        cmd_final = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(merged_raw_video),
            "-i", str(mix_wav_path),
            "-filter_complex", f"[0:v]ass='{escaped_sub}'[v_out]",
            "-map", "[v_out]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", self.cfg.video.preset,
            "-tune", getattr(self.cfg.video, "tune", "animation"),
            "-crf", str(self.cfg.video.crf),
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-pix_fmt", "yuv420p",
            str(final_mp4)
        ]

        res = subprocess.run(cmd_final, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Final muxing failed: {res.stderr}")

        # 10. CapCut Draft export (Permanently disabled as requested)
        # export_to_capcut_draft is omitted to keep workflow lean and pristine

        # 11. Clean up work directory completely to keep output clean
        cleanup_dir(work_story_dir)

        logger.info(f"SUCCESS: Output saved at '{final_mp4}'")
        return final_mp4
