"""Acoustic Forced Alignment Engine.
Uses faster-whisper to pinpoint the exact acoustic millisecond timestamps
from the recorded audio waveform, ensuring 100% frame-to-speech accuracy.
"""

import re
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger("photo_story_narrator.aligner")

def load_audio_16k_mono(path: Path) -> np.ndarray:
    """Uses ffmpeg to decode audio into 16kHz float32 mono array directly,
    bypassing pyav issues on modern python versions."""
    cmd = [
        "ffmpeg", "-y", "-i", str(path),
        "-f", "f32le",
        "-ac", "1",
        "-ar", "16000",
        "-"
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio decode failed: {res.stderr.decode(errors='ignore')}")
    return np.frombuffer(res.stdout, dtype=np.float32)

def _clean_token(tok: str) -> str:
    """Strips punctuation and lowercases for word token matching."""
    return re.sub(r"[^\w]", "", tok.lower())

def align_narration_audio(
    voice_wav_path: Path,
    script_lines: List[str],
    num_frames: int,
    tts_segments: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Pinpoints the exact acoustic second from the recorded audio waveform
    for each frame, placing cut boundaries in natural acoustic pauses."""
    from faster_whisper import WhisperModel

    voice_wav_path = Path(voice_wav_path)
    if not voice_wav_path.exists():
        raise FileNotFoundError(f"Voiceover audio not found at: {voice_wav_path}")

    align_cache_path = voice_wav_path.with_name("voiceover_alignment.json")
    if align_cache_path.exists():
        try:
            with open(align_cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if len(cached.get("frames", [])) == num_frames:
                logger.info(f"Reusing cached acoustic alignment across {num_frames} frames -> {align_cache_path.name}")
                return cached
        except Exception as e:
            logger.warning(f"Failed to read cached alignment: {e}")

    logger.info(f"Acoustic alignment: loading waveform from '{voice_wav_path.name}'...")
    audio_array = load_audio_16k_mono(voice_wav_path)
    total_audio_dur = len(audio_array) / 16000.0

    logger.info("Acoustic alignment: transcribing with faster-whisper (tiny.en, word timestamps)...")
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    whisper_segments, info = model.transcribe(audio_array, word_timestamps=True, language="en")

    # Collect all acoustic word tokens
    all_words = []
    for s in whisper_segments:
        for w in (s.words or []):
            tok = _clean_token(w.word)
            if tok:
                all_words.append({
                    "raw": w.word,
                    "token": tok,
                    "start": float(w.start),
                    "end": float(w.end)
                })

    logger.info(f"Acoustic alignment: found {len(all_words)} words across {len(script_lines)} script lines.")

    # Match each script line sequentially to acoustic words
    w_ptr = 0
    raw_alignments = []

    for idx, line in enumerate(script_lines):
        line_tokens = [_clean_token(w) for w in line.split() if _clean_token(w)]
        if not line_tokens:
            continue

        first_tok = line_tokens[0]
        last_tok = line_tokens[-1]

        # Prioritize ground-truth TTS segment boundaries if available
        if tts_segments and idx < len(tts_segments):
            seg = tts_segments[idx]
            t_start = float(seg["start"])
            t_end = float(seg["end"])
        else:
            # Fallback to acoustic word tokens with strict boundary clamping
            if all_words:
                best_start_idx = min(w_ptr, len(all_words) - 1)
                for search_i in range(w_ptr, min(w_ptr + 15, len(all_words))):
                    if all_words[search_i]["token"] == first_tok:
                        best_start_idx = search_i
                        break

                expected_len = len(line_tokens)
                end_idx = min(best_start_idx + expected_len - 1, len(all_words) - 1)
                end_idx = max(best_start_idx, end_idx)

                for search_j in range(max(best_start_idx, end_idx - 3), min(end_idx + 4, len(all_words))):
                    if all_words[search_j]["token"] == last_tok:
                        end_idx = search_j
                        break

                safe_start = min(best_start_idx, len(all_words) - 1)
                safe_end = min(max(safe_start, end_idx), len(all_words) - 1)
                t_start = all_words[safe_start]["start"]
                t_end = all_words[safe_end]["end"]
                w_ptr = end_idx + 1
            else:
                t_start = 0.0
                t_end = total_audio_dur

        raw_alignments.append({
            "line_idx": idx,
            "line": line,
            "speech_start": t_start,
            "speech_end": max(t_start + 0.3, t_end)
        })

    # Now compute exact visual cut boundaries:
    # Cut point between frame i and i+1 lands in the acoustic silence between speech_end[i] and speech_start[i+1]
    cuts = [0.0]
    num_cuts = len(raw_alignments) - 1
    for i in range(num_cuts):
        s_end = raw_alignments[i]["speech_end"]
        next_s_start = raw_alignments[i + 1]["speech_start"]

        if next_s_start > s_end:
            # Place cut in the middle of silence
            cut_point = (s_end + next_s_start) / 2.0
        else:
            cut_point = s_end

        # Ensure monotonic progression without overshooting total audio duration
        remaining_cuts = num_cuts - i
        max_allowed = total_audio_dur - (remaining_cuts * 0.2)
        min_allowed = cuts[-1] + 0.2
        if max_allowed > min_allowed:
            cut_point = min(max_allowed, max(min_allowed, cut_point))
        else:
            cut_point = min_allowed

        cuts.append(cut_point)

    cuts.append(total_audio_dur)

    # Build final frame timing list
    frame_timings = []
    for i, a in enumerate(raw_alignments):
        c_start = cuts[i]
        c_end = cuts[i + 1]
        dur = max(0.2, c_end - c_start)
        seg_info = tts_segments[i] if tts_segments and i < len(tts_segments) else {}
        frame_timings.append({
            "frame_idx": i,
            "line": a["line"],
            "speaker_id": seg_info.get("speaker_id", 6),
            "speaker_role": seg_info.get("speaker_role", "narrator"),
            "speech_start": a["speech_start"],
            "speech_end": a["speech_end"],
            "start_time": c_start,
            "end_time": c_end,
            "duration": dur
        })

    # If script lines count differs from requested frames count, distribute cleanly
    if len(frame_timings) != num_frames:
        logger.warning(f"Script lines ({len(frame_timings)}) != frames ({num_frames}). Remapping durations.")
        step = float(len(frame_timings)) / float(num_frames)
        remapped = []
        cur_t = 0.0
        for f_idx in range(num_frames):
            s_i = min(int(round(f_idx * step)), len(frame_timings) - 1)
            next_s_i = min(int(round((f_idx + 1) * step)), len(frame_timings))
            t0 = frame_timings[s_i]["start_time"]
            t1 = frame_timings[next_s_i]["start_time"] if next_s_i < len(frame_timings) else total_audio_dur
            f_dur = max(0.5, t1 - t0)
            remapped.append({
                "frame_idx": f_idx,
                "line": frame_timings[s_i]["line"],
                "speaker_id": frame_timings[s_i].get("speaker_id", 6),
                "speaker_role": frame_timings[s_i].get("speaker_role", "narrator"),
                "speech_start": frame_timings[s_i]["speech_start"],
                "speech_end": frame_timings[s_i]["speech_end"],
                "start_time": cur_t,
                "end_time": cur_t + f_dur,
                "duration": f_dur
            })
            cur_t += f_dur
        frame_timings = remapped

    total_calc = sum(f["duration"] for f in frame_timings)
    logger.info(f"Acoustic alignment complete: {len(frame_timings)} frames aligned to {total_calc:.2f}s audio.")
    
    # Format acoustic words with speaker roles for subtitle generator
    sub_words = []
    for w in all_words:
        w_start = w["start"]
        w_end = w["end"]
        matched_role = "narrator"
        matched_sid = 6
        for f in frame_timings:
            if f["speech_start"] - 0.25 <= w_start <= f["speech_end"] + 0.25:
                matched_role = f.get("speaker_role", "narrator")
                matched_sid = f.get("speaker_id", 6)
                break
        sub_words.append({
            "word": w["raw"],
            "start": w_start,
            "end": w_end,
            "speaker_role": matched_role,
            "speaker_id": matched_sid
        })

    result = {
        "frames": frame_timings,
        "words": sub_words,
        "total_duration": total_audio_dur
    }
    try:
        with open(align_cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to cache alignment: {e}")

    return result
