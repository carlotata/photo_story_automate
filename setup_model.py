#!/usr/bin/env python3
"""Downloads the Kokoro TTS ONNX model into assets/kokoro-en-v0_19."""

import sys
import tarfile
import urllib.request
from pathlib import Path

MODEL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-en-v0_19.tar.bz2"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
TARGET_DIR = ASSETS_DIR / "kokoro-en-v0_19"

def download_model():
    if (TARGET_DIR / "model.onnx").exists() and (TARGET_DIR / "voices.bin").exists():
        print(f"[✓] Kokoro ONNX model already installed at: {TARGET_DIR}")
        return

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    tar_path = ASSETS_DIR / "kokoro-en-v0_19.tar.bz2"

    print(f"[*] Downloading Kokoro ONNX model from:\n    {MODEL_URL}")
    print("[*] File size ~330MB. This might take 1-2 minutes...")

    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = downloaded / total_size * 100
            sys.stdout.write(f"\r    Downloading: {percent:.1f}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)")
            sys.stdout.flush()

    urllib.request.urlretrieve(MODEL_URL, tar_path, reporthook=reporthook)
    print("\n[*] Extracting model files...")

    with tarfile.open(tar_path, "r:bz2") as tar:
        tar.extractall(path=ASSETS_DIR)

    if tar_path.exists():
        tar_path.unlink()

    print(f"[✓] Installation complete! Model ready at: {TARGET_DIR}")

if __name__ == "__main__":
    download_model()
