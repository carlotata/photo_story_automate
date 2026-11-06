# Refer to AGENTS.md in root for the complete agent operational specification.
# Key Voice Rules:
# - Repository Default: am_adam (ID: 5)
# - Anishorts Default: am_adam (ID: 5)
# - User Local Default (carlotata): am_michael (ID: 6)
# - Multi-Voice Casting: supports [Narrator], [Girl], [Boy], [Announcement], [Child], [Elder], or Role: "..."
# - Honorifics & Titles: Dr., Sr., Jr., Mr., Mrs., Prof. are auto-expanded to eliminate sentence-stop pauses.
#
# Slash Commands & Pasted Specs Protocol (/photoshorts, /photolong, /shorts, /long, or direct paste):
# 1. Identify format as official script definition, determine Title & Category (Shorts vs Long).
# 2. Set up story folder under input/shorts/<Title>/ or input/long/<Title>/.
# 3. Write script.txt (clean narration) and prompt_spec.txt (full spec).
# 4. Auto-detect and unpack any matching .zip archive (e.g. EPISODE XX.zip) or folder.
# 5. Automatically verify frame parity: len(images) == len(lines), check sequential order.
# 6. IMMEDIATELY RUN THE PIPELINE: Never ask for user approval; execute python run.py /<category> "<Title>" directly.
# 7. DO NOT use Browsentic or any image generation tools; frames are supplied externally.
