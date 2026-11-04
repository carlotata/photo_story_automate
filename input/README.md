# Story Input Directory Guide

This folder holds the assets for your automated video stories. It is categorized into **Short Form** and **Long Form**:

---

## 📱 Short Form: `input/shorts/`
- **Use for**: TikTok, YouTube Shorts, Instagram Reels.
- **Aspect Ratio**: 9:16 Vertical (`1440x2560`).
- **Duration**: **Strictly 59.0 seconds maximum**.
- **Voice Default**: `am_adam` (conversational & punchy).
- **Run Command**:
  ```bash
  python run.py /shorts "YourStoryName"
  # Or simply:
  python run.py /shorts
  ```

---

## 🎬 Long Form: `input/long/`
- **Use for**: Standard YouTube videos, documentaries, video essays.
- **Aspect Ratio**: 16:9 Widescreen 2K (`2560x1440`).
- **Duration**: Uncapped documentary format.
- **Voice Default**: `am_michael` (deep documentary narrator).
- **Run Command**:
  ```bash
  python run.py /long "YourStoryName"
  # Or simply:
  python run.py /long
  ```

---

## 📁 Story Folder Format
Inside either `shorts/` or `long/`, create a folder with your story title:
```
input/shorts/My_Story/
├── Frame_001.jpg
├── Frame_002.jpg
└── script.txt
```
- Each line in `script.txt` corresponds 1:1 to one frame image.
- Final rendered videos are saved into `output/shorts/<Title>/` or `output/long/<Title>/`.
- The `work/` folder is managed automatically by the engine for temporary audio and clip rendering; you do not need to create or edit it.
