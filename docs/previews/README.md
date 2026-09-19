# Emulator captures and layout proofs

`emulator-api34-active.png` / `emulator-api34-ambient.png` are actual 454 × 454 large-round captures. The API 35 pair is the 384 × 384 small-round Wear OS 5.1 emulator. See [validation evidence](../VALIDATION.md) for their source run, measured ambient illumination and limitations. Provider values are emulator data; weather is unavailable. System status indicators belong to Wear OS.

![Actual API 34 active face](emulator-api34-active.png)
![Actual API 35 ambient face](emulator-api35-ambient.png)

## Native editor and interactions

The `*-editor.png` images are the real Wear OS editor, using **system sample readings** for time, health and weather. All six outlined areas independently opened the provider chooser on both emulators. The `*-shortcut-picker.png` images show the bottom shortcut's chooser. `emulator-api34-battery-action.png` records the battery tap opening system Battery settings. The complete per-slot captures and logs are downloadable from the workflow linked in the validation report.

![Native editor with system sample data](emulator-api34-editor.png)

## Edge-caption regression

The `*-edge-alarm.png` images assign the system Alarm provider to the right edge on the disposable emulator. They verify that its “Set” text and the left battery label are fully visible. The default APK still leaves the right edge unassigned.

Weather-tap diagnostics distinguish a request to launch Samsung Weather from a successful app launch. The stock emulators lack the Samsung app; verify the actual destination on Galaxy Watch.

## Illustrative populated-weather layout

`active-illustrative.png` and `ambient-illustrative.png` are **illustrative renders**, not emulator screenshots. They read the committed WFF geometry/colors and use explicit sample data (September 19, 02:26, 71 bpm, 8,420 steps, 62% battery, sample weather). Actual readings always come from Wear OS/providers.

Generated with `tools/render_preview.py --font /path/to/Roboto-Regular.ttf` (Pillow and Node required). Text placement approximates WFF and does not establish platform font metrics, provider behavior, accessibility, or battery use. The active image also serves as the system picker preview. Replace with a verified on-device capture before publishing.

![Illustrative populated weather](active-illustrative.png)
