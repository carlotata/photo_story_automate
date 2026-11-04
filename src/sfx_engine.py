"""Natural Foley & Transition Sound Design Engine.

Generates organic, diegetic sound effects (buzzing alarm clock, mechanical bell,
campfire crackle, pebble clatter, water drips, heavy vault latch, creaking door,
electrical power-down, wet grass footsteps, morning breeze) using mathematical DSP (NumPy).
Accurately aligns transitions with subtle cinematic swells on dissolves
while keeping hard cuts clean, with dynamic vocal ducking.
"""

import math
import wave
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger("photo_story_narrator.sfx")

SAMPLE_RATE = 44100
_rng = np.random.default_rng(2026)

# -------------------------------------------------------------------------
# Mathematical Foley Generators
# -------------------------------------------------------------------------

def foley_buzzing_alarm(duration: float = 0.55) -> np.ndarray:
    """Vibrating digital alarm clock on wooden nightstand."""
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    mod = ((t < 0.22) | ((t > 0.28) & (t < 0.50))).astype(float)
    carrier = np.sin(2 * np.pi * 140 * t) + 0.5 * np.sin(2 * np.pi * 280 * t)
    buzz = np.sign(carrier) * 0.5
    thump = np.sin(2 * np.pi * 55 * t)
    sig = (buzz * 0.7 + thump * 0.3) * mod
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_alarm_bell(duration: float = 0.65) -> np.ndarray:
    """Mechanical twin-bell brass alarm clock hammer ring."""
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    f1, f2 = 1760.0, 1820.0
    ring = (np.sin(2 * np.pi * f1 * t) + 0.8 * np.sin(2 * np.pi * f2 * t)) * np.exp(-t * 6.5)
    strike = np.sin(2 * np.pi * 24 * t)
    sig = ring * (0.6 + 0.4 * strike)
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_notification_ping(duration: float = 0.40) -> np.ndarray:
    """Crisp, high-fidelity digital banking deposit chime."""
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    chime1 = np.sin(2 * np.pi * 1046.5 * t) * np.exp(-t * 12)
    chime2 = np.sin(2 * np.pi * 2093.0 * t) * np.exp(-t * 16)
    sig = chime1 * 0.6 + chime2 * 0.4
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_pebble_clatter(duration: float = 0.45) -> np.ndarray:
    """Small smooth river stones / pebbles clattering on dirt."""
    n = int(duration * SAMPLE_RATE)
    sig = np.zeros(n)
    for i in range(4):
        t0 = 0.05 + i * 0.08 + _rng.uniform(-0.01, 0.02)
        idx = int(t0 * SAMPLE_RATE)
        m = int(0.08 * SAMPLE_RATE)
        tt = np.arange(m) / SAMPLE_RATE
        freq = _rng.uniform(1800, 2600)
        pop = (np.sin(2 * np.pi * freq * tt) + _rng.normal(0, 0.3, m)) * np.exp(-tt * 60)
        sig[idx:idx+m] += pop[:min(m, n - idx)] * _rng.uniform(0.6, 1.0)
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_campfire(duration: float = 1.5) -> np.ndarray:
    """Soft warm campfire flame with intermittent dry wood crackles."""
    n = int(duration * SAMPLE_RATE)
    noise = _rng.normal(0, 1, n)
    s = 0.0
    filtered = np.zeros(n)
    for i in range(n):
        s += 0.015 * (noise[i] - s)
        filtered[i] = s
    crackles = np.zeros(n)
    for _ in range(6):
        pos = int(_rng.uniform(0.1, duration - 0.1) * SAMPLE_RATE)
        w = int(0.02 * SAMPLE_RATE)
        tt = np.arange(w) / SAMPLE_RATE
        crackles[pos:pos+w] += (_rng.normal(0, 1, w) * np.exp(-tt * 150))
    sig = filtered * 0.4 + crackles * 0.55
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_spear_snap(duration: float = 0.25) -> np.ndarray:
    """Dry wooden spear shaft snapping and flint strike."""
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    noise = _rng.normal(0, 1, n) * np.exp(-t * 40)
    snap = np.sin(2 * np.pi * 850 * t) * np.exp(-t * 50)
    sig = noise * 0.6 + snap * 0.4
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_water_drip(duration: float = 0.35) -> np.ndarray:
    """Crisp resonant water droplet falling into pooled liquid."""
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    freq = 1350.0 + 800.0 * (1.0 - np.exp(-t * 45))
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    env = np.exp(-t * 24) * (1.0 - np.exp(-t * 130))
    ripple = 0.28 * np.sin(2 * np.pi * 920.0 * t) * np.exp(-t * 14)
    sig = (np.sin(phase) + ripple) * env
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_vault_latch(duration: float = 0.70) -> np.ndarray:
    """Heavy metallic vault latch mechanism turning and locking/unsealing."""
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    snap = _rng.normal(0, 1, n) * np.exp(-t * 50)
    metal = (
        np.sin(2 * np.pi * 360 * t) * np.exp(-t * 16) +
        0.65 * np.sin(2 * np.pi * 620 * t) * np.exp(-t * 20) +
        0.35 * np.sin(2 * np.pi * 1180 * t) * np.exp(-t * 26)
    )
    thud = np.sin(2 * np.pi * (48 + 65 * np.exp(-t * 14)) * t) * np.exp(-t * 7.5)
    sig = snap * 0.35 + metal * 0.45 + thud * 0.80
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_door_creak(duration: float = 0.90) -> np.ndarray:
    """Natural wooden door hinge friction creak."""
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    freq_mod = 175 + 85 * np.sin(2 * np.pi * 3.8 * t) + 35 * np.sin(2 * np.pi * 9 * t)
    pulse = np.sign(np.sin(2 * np.pi * np.cumsum(freq_mod) / SAMPLE_RATE))
    attack = np.minimum(1.0, t / 0.12)
    decay = np.exp(-np.maximum(0.0, t - 0.12) * 2.5)
    env = attack * decay
    friction = _rng.normal(0, 0.22, n) * env
    sig = (pulse * 0.65 + friction) * env
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_power_down(duration: float = 0.75) -> np.ndarray:
    """Electrical relay switch click and dying capacitor hum."""
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    click = _rng.normal(0, 1, n) * np.exp(-t * 75)
    hum_f = 110.0 * np.exp(-t * 4.5)
    hum = np.sin(2 * np.pi * np.cumsum(hum_f) / SAMPLE_RATE) * np.exp(-t * 4.2)
    sig = click * 0.55 + hum * 0.45
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_screen_tap(duration: float = 0.12) -> np.ndarray:
    """Subtle finger tap on hardened smartphone glass."""
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    glass_ring = np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 55)
    thump = np.sin(2 * np.pi * 220 * t) * np.exp(-t * 40)
    sig = glass_ring * 0.5 + thump * 0.5
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_grass_squish(duration: float = 0.45) -> np.ndarray:
    """Soft wet morning soil and damp grass sock compression."""
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    noise = _rng.normal(0, 1, n)
    s = 0.0
    filtered = np.zeros(n)
    for i in range(n):
        s += 0.07 * (noise[i] - s)
        filtered[i] = s
    sub = np.sin(2 * np.pi * 52 * t) * np.exp(-t * 11)
    sig = (filtered * 0.65 + sub * 0.45) * np.exp(-t * 8.5)
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_wind_breeze(duration: float = 1.4) -> np.ndarray:
    """Soft, gentle morning wind passing through open window or savannah."""
    n = int(duration * SAMPLE_RATE)
    noise = _rng.normal(0, 1, n)
    s = 0.0
    filtered = np.zeros(n)
    for i in range(n):
        s += 0.035 * (noise[i] - s)
        filtered[i] = s
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.8
    sig = filtered * env
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_cinematic_thump(duration: float = 0.65) -> np.ndarray:
    """Subtle, deep 45-65Hz sub-bass impact for dramatic realization beats."""
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    freq = 42.0 + 38.0 * np.exp(-t * 11)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    envelope = np.exp(-t * 6.5)
    sig = np.sin(phase) * envelope
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

def foley_dissolve_swell(duration: float = 0.45) -> np.ndarray:
    """Very soft, gentle cinematic dissolve sweep (whisper level)."""
    n = int(duration * SAMPLE_RATE)
    noise = _rng.normal(0, 1, n)
    s = 0.0
    filtered = np.zeros(n)
    for i in range(n):
        s += 0.04 * (noise[i] - s)
        filtered[i] = s
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 2.0
    sig = filtered * env
    peak = np.abs(sig).max()
    return sig / (peak + 1e-9)

FOLEY_DISPATCH = {
    "buzzing_alarm": foley_buzzing_alarm,
    "alarm_bell": foley_alarm_bell,
    "notification_ping": foley_notification_ping,
    "pebble_clatter": foley_pebble_clatter,
    "campfire": foley_campfire,
    "spear_snap": foley_spear_snap,
    "water_drip": foley_water_drip,
    "vault_latch": foley_vault_latch,
    "door_creak": foley_door_creak,
    "power_down": foley_power_down,
    "screen_tap": foley_screen_tap,
    "grass_squish": foley_grass_squish,
    "wind_breeze": foley_wind_breeze,
    "cinematic_thump": foley_cinematic_thump,
}

def _overlay_signal(base: np.ndarray, sound: np.ndarray, start_time: float, gain: float = 1.0) -> None:
    """Overlays sound into the base buffer at the exact timestamp."""
    start_idx = int(round(start_time * SAMPLE_RATE))
    if start_idx < 0:
        sound = sound[-start_idx:]
        start_idx = 0
    if start_idx >= len(base):
        return

    end_idx = min(len(base), start_idx + len(sound))
    dur = end_idx - start_idx
    if dur > 0:
        base[start_idx:end_idx] += sound[:dur] * gain

def build_natural_soundtrack(
    voice_wav_path: Path,
    output_mix_path: Path,
    scenes_plan: List[Dict[str, Any]],
    foley_master_gain: float = 0.32
) -> Path:
    """
    Renders a natural, perfectly blended soundtrack:
    - Reads the voiceover WAV
    - Places diegetic narrative Foley sounds based on scene director cues
    - Places soft, subtle transition swells ONLY on dissolves (hard cuts remain clean & silent)
    - Applies dynamic voice ducking so voiceover is always crystal clear
    - Normalizes the composite master cleanly to -1.0 dBFS.
    """
    voice_wav_path = Path(voice_wav_path)
    output_mix_path = Path(output_mix_path)
    output_mix_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(voice_wav_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        src_sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)

    dtype = np.int16 if sampwidth == 2 else np.int32
    voice_arr = np.frombuffer(raw_bytes, dtype=dtype).astype(np.float32)
    voice_arr /= (32768.0 if sampwidth == 2 else 2147483648.0)

    if n_channels > 1:
        voice_arr = voice_arr.reshape(-1, n_channels).mean(axis=1)

    if src_sr != SAMPLE_RATE:
        src_len = len(voice_arr)
        target_len = int(round(src_len * SAMPLE_RATE / src_sr))
        voice_arr = np.interp(
            np.linspace(0, src_len, target_len, endpoint=False),
            np.arange(src_len),
            voice_arr
        )

    # Ensure voice track is broadcast-mastered for punch and clarity
    from .tts_engine import master_voice_audio
    voice_arr = master_voice_audio(voice_arr, SAMPLE_RATE)

    total_samples = len(voice_arr)
    total_dur = total_samples / SAMPLE_RATE
    sfx_track = np.zeros(total_samples, dtype=np.float32)

    # 1. Overlay Diegetic Foley Cues
    for sc in scenes_plan:
        sc_start = sc["start_time"]
        for cue in sc.get("foley_cues", []):
            cue_time = sc_start + cue.get("offset", 0.5)
            cue_gain = cue.get("gain", 0.35)
            gen_fn = FOLEY_DISPATCH.get(cue["name"])
            if gen_fn and 0 <= cue_time < total_dur:
                _overlay_signal(sfx_track, gen_fn(), start_time=cue_time, gain=cue_gain)

    # 2. Overlay Transition Sounds (ONLY for dissolves, hard cuts are completely silent)
    for sc in scenes_plan:
        trans_type = sc.get("next_transition", "cut")
        t_dur = sc.get("transition_duration", 0.0)
        if trans_type == "dissolve" and t_dur > 0.1:
            boundary_time = sc["start_time"] + sc["duration"] - t_dur / 2.0
            if 0.2 < boundary_time < (total_dur - 0.3):
                _overlay_signal(
                    sfx_track,
                    foley_dissolve_swell(duration=t_dur),
                    start_time=boundary_time - t_dur / 2.0,
                    gain=0.18
                )

    # 3. Dynamic Vocal Ducking (speech actively dips SFX)
    win_size = int(0.20 * SAMPLE_RATE)
    voice_env = np.convolve(np.abs(voice_arr), np.ones(win_size) / win_size, mode="same")
    ducking = 1.0 - 0.50 * np.clip(voice_env / 0.10, 0.0, 1.0)
    ducked_sfx = np.clip(sfx_track * ducking * foley_master_gain, -0.35, 0.35)

    # 4. Composite voice + SFX
    mixed = voice_arr + ducked_sfx

    # 5. Broadcast Soft-Knee Limiter to -1.0 dBFS (0.89)
    ceiling = 0.89
    peak_val = np.max(np.abs(mixed))
    if peak_val > ceiling:
        mixed = np.tanh(mixed / ceiling) * ceiling

    out_int16 = (np.clip(mixed, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(str(output_mix_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(out_int16.tobytes())

    logger.info(f"Natural soundtrack mastered to '{output_mix_path.name}' ({total_dur:.2f}s)")
    return output_mix_path
