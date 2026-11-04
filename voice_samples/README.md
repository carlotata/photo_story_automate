# Kokoro Voice Gallery (Voice Samples)

Listen to each audio sample below to choose the voice that best fits your story.
Every sample speaks the following test lines with year and time normalization:
> *"Hello, I am [Name], Voice ID [ID]. Back in nineteen fifty, waking up at two a.m. was not insomnia. By twenty twenty-six, we are bringing history back to life."*

---

| Voice ID | Speaker Name | Accent / Gender | Style Description | Sample WAV Link |
|:---:|:---|:---|:---|:---|
| **0** | `af_alloy` | American Female | Neutral, clear, modern explainer | [voice_00_af_alloy.wav](file:///D:/VS%20CODE%20PROJECTS/ANTIGRAVITY-AUTOMATION/photo_story_narrator/voice_samples/voice_00_af_alloy.wav) |
| **1** | `af_bella` | American Female | Warm, emotive, expressive storytelling | [voice_01_af_bella.wav](file:///D:/VS%20CODE%20PROJECTS/ANTIGRAVITY-AUTOMATION/photo_story_narrator/voice_samples/voice_01_af_bella.wav) |
| **2** | `af_heart` | American Female | Soft, calm, gentle meditation / ASMR | [voice_02_af_heart.wav](file:///D:/VS%20CODE%20PROJECTS/ANTIGRAVITY-AUTOMATION/photo_story_narrator/voice_samples/voice_02_af_heart.wav) |
| **3** | `af_nicole` | American Female | Gentle, intimate, whispering warmth | [voice_03_af_nicole.wav](file:///D:/VS%20CODE%20PROJECTS/ANTIGRAVITY-AUTOMATION/photo_story_narrator/voice_samples/voice_03_af_nicole.wav) |
| **4** | `af_sarah` | American Female | Confident, articulate, professional | [voice_04_af_sarah.wav](file:///D:/VS%20CODE%20PROJECTS/ANTIGRAVITY-AUTOMATION/photo_story_narrator/voice_samples/voice_04_af_sarah.wav) |
| **5** | `am_adam` | American Male | Crisp, conversational, dynamic explainer | [voice_05_am_adam.wav](file:///D:/VS%20CODE%20PROJECTS/ANTIGRAVITY-AUTOMATION/photo_story_narrator/voice_samples/voice_05_am_adam.wav) |
| **6** | `am_michael` | American Male | **Deep Documentary Narrator (Default)** | [voice_06_am_michael.wav](file:///D:/VS%20CODE%20PROJECTS/ANTIGRAVITY-AUTOMATION/photo_story_narrator/voice_samples/voice_06_am_michael.wav) |
| **7** | `bf_emma` | British Female | Articulate, sophisticated, documentary | [voice_07_bf_emma.wav](file:///D:/VS%20CODE%20PROJECTS/ANTIGRAVITY-AUTOMATION/photo_story_narrator/voice_samples/voice_07_bf_emma.wav) |
| **8** | `bf_isabella` | British Female | Melodic, vivid, engaging storyteller | [voice_08_bf_isabella.wav](file:///D:/VS%20CODE%20PROJECTS/ANTIGRAVITY-AUTOMATION/photo_story_narrator/voice_samples/voice_08_bf_isabella.wav) |
| **9** | `bm_george` | British Male | Deep, resonant, historical period narrator | [voice_09_bm_george.wav](file:///D:/VS%20CODE%20PROJECTS/ANTIGRAVITY-AUTOMATION/photo_story_narrator/voice_samples/voice_09_bm_george.wav) |
| **10** | `bm_lewis` | British Male | Smooth, composed, classical British voice | [voice_10_bm_lewis.wav](file:///D:/VS%20CODE%20PROJECTS/ANTIGRAVITY-AUTOMATION/photo_story_narrator/voice_samples/voice_10_bm_lewis.wav) |

---

### How to Use Any Voice in Your Renders:
Pass `--voice <ID>` or `-v <ID>` when running `run.py`:
```powershell
# Example: Use British Male George (ID 9)
python run.py "Your Story Title" --voice 9

# Example: Use American Female Bella (ID 1)
python run.py "Your Story Title" --voice 1

# Default is am_michael (ID 6)
python run.py "Your Story Title"
```
