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

ONES = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
        'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
        'seventeen', 'eighteen', 'nineteen']
TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
ORDINALS = {
    '1st': 'first', '2nd': 'second', '3rd': 'third', '4th': 'fourth', '5th': 'fifth',
    '6th': 'sixth', '7th': 'seventh', '8th': 'eighth', '9th': 'ninth', '10th': 'tenth',
    '11th': 'eleventh', '12th': 'twelfth', '13th': 'thirteenth', '14th': 'fourteenth',
    '15th': 'fifteenth', '16th': 'sixteenth', '17th': 'seventeenth', '18th': 'eighteenth',
    '19th': 'nineteenth', '20th': 'twentieth', '21st': 'twenty-first'
}

def year_num_to_words(y: int) -> str:
    if 1000 <= y <= 2099:
        century = y // 100
        decade = y % 100
        if y == 2000:
            return 'two thousand'
        if 2001 <= y <= 2009:
            return f'two thousand {ONES[decade]}'
        c_str = ONES[century] if century < 20 else f'{TENS[century//10]} {ONES[century%10]}'.strip()
        if decade == 0:
            return f'{c_str} hundred'
        elif decade < 20:
            return f'{c_str} {ONES[decade]}'
        else:
            d_str = f'{TENS[decade//10]} {ONES[decade%10]}'.strip()
            return f'{c_str} {d_str}'
    return str(y)

def replace_year(match):
    prefix = match.group(1) or ""
    year_str = match.group(2)
    suffix = match.group(3)
    y = int(year_str)
    w = year_num_to_words(y)
    if suffix:  # 1890s -> eighteen nineties
        if w.endswith('y'):
            w = w[:-1] + 'ies'
        elif w.endswith('hundred'):
            w = w + 's'
        else:
            w = w + 's'
    return f'{prefix}{w}'

def normalize_tts_text(text: str) -> str:
    """Normalizes colloquial, shorthand, year, and time patterns for natural TTS speech.
    - Converts '2:00 a.m.' -> '2 a.m.' so Kokoro doesn't say 'two zero zero a.m.'.
    - Converts 'in 1500' / 'by 1950' / 'in 2026' -> 'in fifteen hundred' / 'by nineteen fifty' / 'by twenty twenty six'.
    - Converts '1890s' / '1950s' -> 'eighteen nineties' / 'nineteen fifties'.
    - Converts '14th century' -> 'fourteenth century'.
    """
    # 1. Clock times: 2:00 a.m. / 2:00 AM -> 2 a.m. / 2 AM
    text = re.sub(r'\b(\d{1,2}):00\s*([ap]\.?m\.?)\b', r'\1 \2', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(\d{1,2}):00\b', r"\1 o'clock", text)

    # 2. Ordinals: 14th century -> fourteenth century
    for ord_digit, ord_word in ORDINALS.items():
        text = re.sub(rf'\b{ord_digit}\b', ord_word, text, flags=re.IGNORECASE)

    # 3. 4-Digit Years: e.g. in 1500, year 1500, by 1850, in the 1990s, by 2026
    text = re.sub(r'\b(in\s+|year\s+|by\s+|since\s+|during\s+|around\s+|from\s+|to\s+)?(1[0-9]{3}|20[0-9]{2})(s)?\b', replace_year, text, flags=re.IGNORECASE)

    return text

def master_voice_audio(audio: np.ndarray, sample_rate: int = 24000) -> np.ndarray:
    """Applies broadcast voice processing: DC-offset removal, transparent RMS leveling,
    and soft-knee limiting to bring active speech to industry-standard ~-16 dBFS
    with true peaks capped at -1.0 dBFS (0.89).
    """
    if len(audio) == 0:
        return audio
    
    # 1. Remove DC offset
    audio = audio - np.mean(audio)
    
    # 2. Measure active speech RMS (filtering out silence/gaps)
    abs_audio = np.abs(audio)
    speech_mask = abs_audio > 0.005
    active_rms = np.sqrt(np.mean(audio[speech_mask]**2)) if np.any(speech_mask) else np.sqrt(np.mean(audio**2))
    
    # 3. Target active RMS: 0.155 (~ -16.2 dBFS / -14 to -15 LUFS standard)
    target_rms = 0.155
    gain = min(5.0, target_rms / max(1e-4, active_rms))
    boosted = audio * gain
    
    # 4. Transparent soft-knee compression on peaks above ceiling (0.89 = -1.0 dBFS)
    ceiling = 0.89
    peak_val = np.max(np.abs(boosted))
    if peak_val > ceiling:
        boosted = np.tanh(boosted / ceiling) * ceiling
        
    return boosted

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
                text = normalize_tts_text(text)
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
        line = normalize_tts_text(line)
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
                line_tts = normalize_tts_text(line)
                audio = self._tts.generate(line_tts, sid=self.config.speaker_id, speed=self.config.speed)
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

        # Combine audio and master to broadcast loudness standard
        full_audio = np.concatenate(audio_chunks)
        full_audio = master_voice_audio(full_audio, sr)

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
