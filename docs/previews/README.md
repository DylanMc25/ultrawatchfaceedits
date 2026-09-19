# Emulator captures and layout proofs

`emulator-api34-active.png` / `emulator-api34-ambient.png` are actual 454 × 454 large-round captures. The API 35 pair is the 384 × 384 small-round Wear OS 5.1 emulator. See [validation evidence](../VALIDATION.md) for their source run, measured ambient illumination and limitations. Provider values are emulator data; weather is unavailable. System status indicators belong to Wear OS.

![Actual API 34 active face](emulator-api34-active.png)
![Actual API 35 ambient face](emulator-api35-ambient.png)

## Illustrative populated-weather layout

`active-illustrative.png` and `ambient-illustrative.png` are **illustrative renders**, not emulator screenshots. They read the committed WFF geometry/colors and use explicit sample data (September 19, 02:26, 71 bpm, 8,420 steps, 62% battery, sample weather). Actual readings always come from Wear OS/providers.

Generated with `tools/render_preview.py --font /path/to/Roboto-Regular.ttf` (Pillow and Node required). Text placement approximates WFF and does not establish platform font metrics, provider behavior, accessibility, or battery use. The active image also serves as the system picker preview. Replace with a verified on-device capture before publishing.

![Illustrative populated weather](active-illustrative.png)
