"""TTS Engine using Kokoro via sherpa-onnx for deep realistic male voice narration."""

import os
import re
import wave
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from .config import VoiceConfig, VOICE_ROLE_MAPPING

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

ABBREVIATIONS = [
    (r'\bDr\.\s*', 'Doctor '),
    (r'\bMr\.\s*', 'Mister '),
    (r'\bMrs\.\s*', 'Missus '),
    (r'\bMs\.\s*', 'Ms '),
    (r'\bProf\.\s*', 'Professor '),
    (r'\bCapt\.\s*', 'Captain '),
    (r'\bGen\.\s*', 'General '),
    (r'\bCol\.\s*', 'Colonel '),
    (r'\bLt\.\s*', 'Lieutenant '),
    (r'\bSgt\.\s*', 'Sergeant '),
    (r'\bRev\.\s*', 'Reverend '),
    (r'\bSt\.\s+(?=[A-Z])', 'Saint '),
    (r'\bvs\.\s*', 'versus '),
    (r'\betc\.\s*', 'etcetera '),
    (r'\be\.g\.,?\s*', 'for example '),
    (r'\bi\.e\.,?\s*', 'that is '),
    (r'\bNo\.\s*(\d+)', r'number \1'),
    (r'\b(Jr|Sr)\.\s*(?=[A-Za-z0-9])', lambda m: ('Senior ' if m.group(1).lower() == 'sr' else 'Junior ')),
    (r'\b(Jr|Sr)\.\s*([,;])\s*', lambda m: ('Senior' if m.group(1).lower() == 'sr' else 'Junior') + m.group(2) + ' '),
    (r'\b(Jr|Sr)\.\s*(\.|\Z)', lambda m: ('Senior.' if m.group(1).lower() == 'sr' else 'Junior.')),
]

def expand_titles_and_abbreviations(text: str) -> str:
    """Expands titles and abbreviations (Dr., Sr., Jr., Mr., etc.) so Kokoro doesn't treat
    them as sentence terminators or add awkward acoustic silences."""
    for pat, repl in ABBREVIATIONS:
        if callable(repl):
            text = re.sub(pat, repl, text, flags=re.IGNORECASE)
        else:
            text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    return text

def parse_cast_header(raw_text: str) -> Dict[str, str]:
    """Parses optional '# CAST: Alice=af_bella, Bob=am_adam' header from scripts."""
    cast = {}
    for line in raw_text.splitlines():
        line = line.strip()
        m = re.match(r'^\s*#\s*(?:CAST|VOICES?)\s*:\s*(.*)', line, re.I)
        if m:
            entries = m.group(1).split(',')
            for entry in entries:
                if '=' in entry:
                    name, voice = entry.split('=', 1)
                    cast[name.strip().lower()] = voice.strip().lower()
    return cast

def resolve_speaker(role_or_id: Any, custom_cast: Optional[Dict[str, str]] = None, default_id: int = 6) -> Tuple[int, str]:
    """Resolves role names, character names, or voice IDs to Kokoro (speaker_id, speaker_role)."""
    if role_or_id is None:
        return default_id, 'narrator'
    r = str(role_or_id).strip().lower()
    if custom_cast and r in custom_cast:
        return resolve_speaker(custom_cast[r], custom_cast=None, default_id=default_id)
    if r.isdigit():
        return int(r), 'custom'
    if r in VOICE_ROLE_MAPPING:
        return VOICE_ROLE_MAPPING[r], r
    return default_id, 'narrator'

def parse_line_speaker_chunks(
    raw_line: str,
    custom_cast: Optional[Dict[str, str]] = None,
    default_id: int = 6
) -> List[Dict[str, Any]]:
    """Splits a single frame line into speaker chunks, supporting:
    1. Bracketed tags: [Girl] "Help!" or [Narrator] "He turned." [Girl] "Run!"
    2. Colon prefixes: Girl: "Wait for me!"
    3. Standard text: defaults to primary narrator voice.
    """
    line = raw_line.strip()
    
    # 1. Bracketed tags anywhere in line: e.g. [Narrator] text [Girl] dialogue
    tokens = re.split(r'(\[[a-zA-Z0-9_\-\s]+\])', line)
    if len(tokens) > 1:
        parts = []
        current_speaker_id = default_id
        current_role = 'narrator'
        for tok in tokens:
            tok = tok.strip()
            if not tok:
                continue
            m_tag = re.match(r'^\[([a-zA-Z0-9_\-\s]+)\]$', tok)
            if m_tag:
                tag_name = m_tag.group(1).strip()
                current_speaker_id, current_role = resolve_speaker(tag_name, custom_cast, default_id)
            else:
                clean_t = tok.strip(' "\'“”')
                if clean_t:
                    parts.append({
                        "speaker_id": current_speaker_id,
                        "speaker_role": current_role,
                        "text": clean_t
                    })
        if parts:
            return parts

    # 2. Prefix role tag: Role: "..." or Role: ...
    m_prefix = re.match(r'^([a-zA-Z0-9_\-\s]{2,25})\s*:\s*["“]?(.*?)["”]?$', line)
    if m_prefix:
        prefix_tag = m_prefix.group(1).strip()
        body_text = m_prefix.group(2).strip(' "\'“”')
        if (custom_cast and prefix_tag.lower() in custom_cast) or (prefix_tag.lower() in VOICE_ROLE_MAPPING):
            sid, role = resolve_speaker(prefix_tag, custom_cast, default_id)
            return [{
                "speaker_id": sid,
                "speaker_role": role,
                "text": body_text
            }]

    # 3. Standard fallback: single chunk with default speaker
    clean_text = line.strip(' "\'“”')
    return [{
        "speaker_id": default_id,
        "speaker_role": 'narrator',
        "text": clean_text
    }]

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
    """Normalizes colloquial, shorthand, year, time, and title patterns for natural TTS speech.
    - Expands 'Dr.', 'Sr.', 'Jr.', 'Mr.', 'Mrs.', etc. to prevent sentence-terminator pauses.
    - Converts '2:00 a.m.' -> '2 a.m.' so Kokoro doesn't say 'two zero zero a.m.'.
    - Converts 'in 1500' / 'by 1950' / 'in 2026' -> 'in fifteen hundred' / 'by nineteen fifty' / 'by twenty twenty six'.
    - Converts '1890s' / '1950s' -> 'eighteen nineties' / 'nineteen fifties'.
    - Converts '14th century' -> 'fourteenth century'.
    """
    # 0. Titles & Abbreviations (removes hard pause period)
    text = expand_titles_and_abbreviations(text)

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

def parse_script_into_frames(
    raw_text: str,
    custom_cast: Optional[Dict[str, str]] = None,
    default_id: int = 6
) -> List[Dict[str, Any]]:
    """Parses raw script text into structured frames with speaker assignments and clean text.
    Guarantees 1:1 frame parity with clean_script_text."""
    if custom_cast is None:
        custom_cast = parse_cast_header(raw_text)

    frames = []
    lines = raw_text.strip().splitlines()

    # 1. Check for NARRATION: "..." lines in full episode specs
    narration_matches = re.findall(r'NARRATION:\s*["“]([\s\S]*?)["”]', raw_text, re.IGNORECASE)
    if narration_matches:
        for idx, text in enumerate(narration_matches):
            text = re.sub(r'\s+', ' ', text)
            chunks = parse_line_speaker_chunks(text, custom_cast, default_id)
            for c in chunks:
                c["text"] = normalize_tts_text(c["text"]).strip()
            chunks = [c for c in chunks if c["text"]]
            if not chunks:
                continue
            clean_line = " ".join(c["text"] for c in chunks)
            frames.append({
                "line_idx": idx,
                "clean_line": clean_line,
                "primary_speaker_id": chunks[0]["speaker_id"],
                "primary_speaker_role": chunks[0]["speaker_role"],
                "chunks": chunks
            })
        if frames:
            return frames

    # 2. Check for explicit VOICEOVER: block in spec
    vo_match = re.search(r'VOICEOVER:\s*([\s\S]*?)(?=\n\s*(?:SETUP NOTE:|\+---|[A-Z0-9_]{3,}:)|\Z)', raw_text, re.IGNORECASE)
    if vo_match and len(vo_match.group(1).strip().split()) > 10:
        vo_body = vo_match.group(1).strip()
        vo_body = expand_titles_and_abbreviations(vo_body)
        # Split on sentence boundaries, protected against single initials & abbreviations
        sentences = [s.strip() for s in re.split(r'(?<!\b[A-Za-z])(?<=[.!?])\s+', vo_body) if s.strip()]
        for idx, s in enumerate(sentences):
            chunks = parse_line_speaker_chunks(s, custom_cast, default_id)
            for c in chunks:
                c["text"] = normalize_tts_text(c["text"]).strip()
            chunks = [c for c in chunks if c["text"]]
            if not chunks:
                continue
            clean_line = " ".join(c["text"] for c in chunks)
            frames.append({
                "line_idx": idx,
                "clean_line": clean_line,
                "primary_speaker_id": chunks[0]["speaker_id"],
                "primary_speaker_role": chunks[0]["speaker_role"],
                "chunks": chunks
            })
        if frames:
            return frames

    # 3. Check if script uses the instructional Frame_XXX = "..." format
    has_frame_assignments = any(re.search(r"^\s*[-*•]?\s*Frame[-_]?\d+\s*=", l, re.I) for l in lines)
    if has_frame_assignments:
        frame_idx = 0
        for line in lines:
            line = line.strip()
            m = re.search(r'^\s*[-*•]?\s*Frame[-_]?\d+\s*=\s*(.*)', line, re.I)
            if m:
                raw_val = m.group(1).strip()
                m_q = re.match(r'^(["\'])(.*?)\1$', raw_val)
                raw_content = m_q.group(2) if m_q else raw_val
                chunks = parse_line_speaker_chunks(raw_content, custom_cast, default_id)
                for c in chunks:
                    c["text"] = normalize_tts_text(c["text"]).strip()
                chunks = [c for c in chunks if c["text"]]
                if not chunks:
                    continue
                clean_line = " ".join(c["text"] for c in chunks)
                frames.append({
                    "line_idx": frame_idx,
                    "clean_line": clean_line,
                    "primary_speaker_id": chunks[0]["speaker_id"],
                    "primary_speaker_role": chunks[0]["speaker_role"],
                    "chunks": chunks
                })
                frame_idx += 1
        return frames

    # 4. Standard format: 1 line = 1 frame
    frame_idx = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if re.match(r"^SEGMENT\s+\d+", line, re.I):
            continue
        chunks = parse_line_speaker_chunks(line, custom_cast, default_id)
        for c in chunks:
            c["text"] = normalize_tts_text(c["text"]).strip()
        chunks = [c for c in chunks if c["text"]]
        if not chunks:
            continue
        clean_line = " ".join(c["text"] for c in chunks)
        frames.append({
            "line_idx": frame_idx,
            "clean_line": clean_line,
            "primary_speaker_id": chunks[0]["speaker_id"],
            "primary_speaker_role": chunks[0]["speaker_role"],
            "chunks": chunks
        })
        frame_idx += 1
    return frames

def clean_script_text(raw_text: str) -> List[str]:
    """Splits raw text into natural narration lines, stripping comments, stage cues,
    and speaker tags, while expanding title abbreviations (Dr., Sr., Jr., etc.)."""
    frames = parse_script_into_frames(raw_text)
    return [f["clean_line"] for f in frames]

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
        """Generates synchronized voiceover audio supporting multi-character dialogue
        and returns timing and speaker metadata."""
        output_wav_path = Path(output_wav_path)
        output_wav_path.parent.mkdir(parents=True, exist_ok=True)
        meta_json = output_wav_path.with_suffix(".json")

        parsed_frames = parse_script_into_frames(
            script_text,
            custom_cast=self.config.custom_cast,
            default_id=self.config.speaker_id
        )
        if not parsed_frames:
            raise ValueError("Script is empty after cleaning.")

        if output_wav_path.exists() and meta_json.exists():
            try:
                with open(meta_json, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if len(cached.get("segments", [])) == len(parsed_frames):
                    logger.info(f"Reusing cached voiceover audio ({cached.get('total_duration', 0):.2f}s) across {len(parsed_frames)} segments -> {output_wav_path.name}")
                    return cached
            except Exception as e:
                logger.warning(f"Failed to read cached voiceover metadata: {e}")

        sr = self._tts.sample_rate
        audio_chunks = []
        segments = []
        words_metadata = []
        cur_time = 0.0
        gap_samples = np.zeros(int(sr * 0.28), dtype=np.float32)
        micro_gap = np.zeros(int(sr * 0.12), dtype=np.float32)

        for line_idx, frame_info in enumerate(parsed_frames):
            frame_chunks = frame_info["chunks"]
            frame_spoken_text = frame_info["clean_line"]
            primary_speaker_id = frame_info["primary_speaker_id"]
            primary_speaker_role = frame_info["primary_speaker_role"]

            frame_samples_list = []
            for c_idx, chunk in enumerate(frame_chunks):
                chunk_tts = chunk["text"]
                try:
                    audio = self._tts.generate(chunk_tts, sid=chunk["speaker_id"], speed=self.config.speed)
                    samples = np.array(audio.samples, dtype=np.float32)
                    frame_samples_list.append(samples)
                    if c_idx < len(frame_chunks) - 1:
                        frame_samples_list.append(micro_gap)
                except Exception as e:
                    logger.error(f"Error generating TTS for line {line_idx} chunk {c_idx}: {e}")

            if not frame_samples_list:
                continue

            frame_samples = np.concatenate(frame_samples_list)
            seg_start = cur_time
            seg_dur = len(frame_samples) / sr
            seg_end = seg_start + seg_dur

            segments.append({
                "line_idx": line_idx,
                "text": frame_spoken_text,
                "speaker_id": primary_speaker_id,
                "speaker_role": primary_speaker_role,
                "start": seg_start,
                "end": seg_end,
                "duration": seg_dur
            })

            # Estimate word-level timestamps weighted by character length
            raw_words = frame_spoken_text.split()
            if raw_words:
                total_chars = sum(len(w) + 1 for w in raw_words)
                w_start = seg_start
                for w in raw_words:
                    w_dur = seg_dur * ((len(w) + 1) / total_chars)
                    words_metadata.append({
                        "word": w,
                        "start": w_start,
                        "end": w_start + w_dur,
                        "line_idx": line_idx,
                        "speaker_id": primary_speaker_id,
                        "speaker_role": primary_speaker_role
                    })
                    w_start += w_dur

            audio_chunks.append(frame_samples)
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
        logger.info(f"Generated multi-voice narration: {total_duration:.2f}s across {len(segments)} frames -> {output_wav_path.name}")

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
