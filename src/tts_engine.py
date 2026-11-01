"""TTS Engine using Kokoro via sherpa-onnx for deep realistic male voice narration."""

import os
import re
import wave
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np

from .config import VoiceConfig

logger = logging.getLogger("photo_story_narrator.tts")

def clean_script_text(raw_text: str) -> List[str]:
    """Splits raw text into natural narration lines, stripping comments and stage cues.
    Directly supports instructional Frame_XXX = "..." syntax (1 line = 1 frame).
    """
    cleaned_lines = []
    lines = raw_text.strip().splitlines()

    # Check if script uses the instructional Frame_XXX = "..." format
    has_frame_assignments = any(re.search(r"^\s*[-*•]?\s*Frame[-_]?\d+\s*=", l, re.I) for l in lines)

    if has_frame_assignments:
        for line in lines:
            line = line.strip()
            # Match Frame_001 = "Narration text" or - Frame_001 = "Narration text"
            m = re.search(r"^\s*[-*•]?\s*Frame[-_]?\d+\s*=\s*[\"'](.*?)[\"']", line, re.I)
            if m:
                text = m.group(1).strip()
                # Strip bracketed cues inside quotes
                text = re.sub(r"\[.*?\]", "", text)
                text = re.sub(r"\(.*?\)", "", text)
                text = text.strip()
                if text:
                    cleaned_lines.append(text)
        return cleaned_lines

    # Standard format: 1 line = 1 frame
    for line in lines:
        line = line.strip()
        # Skip comments, rules headers, segment headers, and empty lines
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if re.match(r"^SEGMENT\s+\d+", line, re.I):
            continue
        # Remove bracketed cues like [Music], [Scene 1], (whispering), etc.
        line = re.sub(r"\[.*?\]", "", line)
        line = re.sub(r"\(.*?\)", "", line)
        line = line.strip()
        if not line:
            continue
        cleaned_lines.append(line)
    return cleaned_lines

class TTSEngine:
    def __init__(self, config: VoiceConfig):
        self.config = config
        self.model_dir = Path(config.model_dir)
        self._tts = None
        self._init_engine()

    def _init_engine(self):
        try:
            import sherpa_onnx
        except ImportError:
            raise RuntimeError("sherpa-onnx is not installed. Please run: pip install sherpa-onnx")

        d = str(self.model_dir.resolve())
        model_file = f"{d}/model.onnx"
        voices_file = f"{d}/voices.bin"
        tokens_file = f"{d}/tokens.txt"
        data_dir = f"{d}/espeak-ng-data"

        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Kokoro model file not found at: {model_file}")

        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                    model=model_file,
                    voices=voices_file,
                    tokens=tokens_file,
                    data_dir=data_dir
                ),
                num_threads=4,
                provider="cpu"
            )
        )
        self._tts = sherpa_onnx.OfflineTts(tts_config)
        logger.info(f"Initialized Kokoro TTS (Speaker ID: {self.config.speaker_id} - {self.config.speaker_name})")

    def generate_narration(
        self,
        script_text: str,
        output_wav_path: Path
    ) -> Dict[str, Any]:
        """Generates synchronized voiceover audio and returns timing metadata."""
        output_wav_path = Path(output_wav_path)
        output_wav_path.parent.mkdir(parents=True, exist_ok=True)
        meta_json = output_wav_path.with_suffix(".json")

        lines = clean_script_text(script_text)
        if not lines:
            raise ValueError("Script is empty after cleaning.")

        if output_wav_path.exists() and meta_json.exists():
            try:
                with open(meta_json, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if len(cached.get("segments", [])) == len(lines):
                    logger.info(f"Reusing cached voiceover audio ({cached.get('total_duration', 0):.2f}s) across {len(lines)} segments -> {output_wav_path.name}")
                    return cached
            except Exception as e:
                logger.warning(f"Failed to read cached voiceover metadata: {e}")

        sr = self._tts.sample_rate
        audio_chunks = []
        segments = []
        words_metadata = []
        cur_time = 0.0
        gap_samples = np.zeros(int(sr * 0.28), dtype=np.float32)

        for line_idx, line in enumerate(lines):
            try:
                audio = self._tts.generate(line, sid=self.config.speaker_id, speed=self.config.speed)
                samples = np.array(audio.samples, dtype=np.float32)
            except Exception as e:
                logger.error(f"Error generating TTS for line {line_idx}: {e}")
                continue

            seg_start = cur_time
            seg_dur = len(samples) / sr
            seg_end = seg_start + seg_dur

            segments.append({
                "line_idx": line_idx,
                "text": line,
                "start": seg_start,
                "end": seg_end,
                "duration": seg_dur
            })

            # Estimate word-level timestamps weighted by character length
            raw_words = line.split()
            if raw_words:
                total_chars = sum(len(w) + 1 for w in raw_words)
                w_start = seg_start
                for w in raw_words:
                    w_dur = seg_dur * ((len(w) + 1) / total_chars)
                    words_metadata.append({
                        "word": w,
                        "start": w_start,
                        "end": w_start + w_dur,
                        "line_idx": line_idx
                    })
                    w_start += w_dur

            audio_chunks.append(samples)
            audio_chunks.append(gap_samples)
            cur_time += seg_dur + 0.28

        # Combine audio and normalize peak
        full_audio = np.concatenate(audio_chunks)
        peak = max(1e-6, np.abs(full_audio).max())
        full_audio = full_audio / peak * 0.95

        # Write WAV file
        with wave.open(str(output_wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes((full_audio * 32767).astype(np.int16).tobytes())

        total_duration = len(full_audio) / sr
        logger.info(f"Generated voiceover: {total_duration:.2f}s across {len(segments)} segments -> {output_wav_path.name}")

        result_meta = {
            "wav_path": str(output_wav_path),
            "total_duration": total_duration,
            "sample_rate": sr,
            "segments": segments,
            "words": words_metadata
        }
        try:
            with open(meta_json, "w", encoding="utf-8") as f:
                json.dump(result_meta, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not write voiceover metadata JSON: {e}")

        return result_meta
