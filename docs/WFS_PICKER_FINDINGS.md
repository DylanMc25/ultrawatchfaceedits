# Test.wfs: complication selection investigation

Inspected 2026-09-26 against repository version 13 (`3af6288`). This is a research checkpoint; no watch-face behavior, assignments, or layout changed.

## What the supplied project contains

The supplied `Test.wfs` is a ZIP with 81 entries, including `honeyface.json` (project file version `1.120909`), previews, artwork and editor metadata. Its SHA-256 is `5c0eeea4fbe73df6920c76aef9e22d2cf721f77d81499a746235ab3dce641013`. The original project and artwork are not redistributed in this repository.

There are seven `complicationSlot` objects. The table lists **activated** formats, not every format stored in the project. WFS retains disabled formats and their layouts too; counting all stored layouts would overstate what the picker accepts.

| Project slot | Activated formats, in priority order | Default provider | Fixed? |
| --- | --- | --- | --- |
| Circle Complication Down | Short text, icon | Heart rate | No |
| Circle Complication Up | Short text, icon | Sunrise/sunset | No |
| Left Edge Complication | Ranged value, goal progress | Watch battery | No |
| Right Edge Complication | Ranged value, goal progress | Step count | No |
| Large Box Complication | Long text, ranged value, small image | Empty | No |
| Small Box Complication | Short text, small image, icon, ranged value | Empty | No |
| Line Complication | Short text | Empty | No |

Reproduce these findings by reading each slot's `complicationTypeOrder`, filtering it by `complicationTypes[type].activated`, and inspecting `categories.complicationSlotPreview.properties`. The latter contains `defaultProvider.value`, `fixedProvider.value` and `isFixed.value`.

All seven `isFixed.value` fields are false. All seven also contain a dormant `fixedProvider` value of `WATCH_BATTERY`; those values are **not** seven restrictions to battery. Likewise, `fixedComplicationType` is present even on editable slots and is not evidence of an allowed-provider list. The project has color/font styles and complication default presets; no provider allowlist was found.

## The pictured forecast is separate from the Large Box

The scene contains independent groups named `Weather Current`, `Weather In 2 Hours`, `Weather In 4 Hours`, `Weather In 6 Hours` and `Weather Current(Temperature)`. They use weather expressions including `[WTHR_TEM]`, `[WTHR_COND]` and `forecastHours(2,"COND")`, with equivalent four- and six-hour expressions.

Those groups are siblings of the complication slots. The `Large Box Complication` is a separate scene item, initially assigned Empty. Thus the forecast visible in the project preview does not demonstrate a forecast provider selected into that rectangle. Copying that arrangement would not, by itself, make the weather replaceable through the ordinary complication picker.

## What the controls establish

Samsung documents Editable/Fixed, supported formats, their priority, defaults and component layouts. Fixed prevents the wearer from changing the provider. Format priority chooses the representation when a provider offers multiple formats; defaults choose the initial assignment. Shape controls the visible area and available layouts. None of these documented WFS settings is an allowlist of apps. [Samsung WFS complications guide](https://developer.samsung.com/watch-face-studio/user-guide/complications.html)

WFF exposes `supportedTypes` and `isCustomizable`. The latter controls whether the wearer can replace a provider. `DefaultProviderPolicy` supplies initial providers and fallbacks, not permitted replacements. [ComplicationSlot](https://developer.android.com/reference/wear-os/wff/complication/complication-slot), [DefaultProviderPolicy](https://developer.android.com/reference/wear-os/wff/complication/default-provider-policy)

Wear OS matches the slot's supported types against each data source's supported types. Without a match, the source is ineligible; otherwise the first matching slot type is selected. A provider configuration activity runs after that provider is selected, so it cannot prune the preceding system picker. `SAFE_WATCH_FACES` governs provider trust and delivery, not a face-owned app allowlist. [ComplicationDataSourceService](https://developer.android.com/reference/androidx/wear/watchface/complications/datasource/ComplicationDataSourceService)

## Comparison with our current face

| Area | Current implementation | Useful lesson from this project |
| --- | --- | --- |
| Weather rectangle, Wear OS 6 bundled face | `SMALL_IMAGE EMPTY` | Already narrower than the project's Large Box. Adding its long-text/ranged formats would broaden provider eligibility. A small-image format does not mean “rectangular charts only”; app icons can use it too. |
| Shortcut | `SMALL_IMAGE EMPTY` | The same format is needed for the current App shortcut support. Making it a Line would exclude image-only providers, including our current shortcut path. |
| Edges | Short text, ranged value, goal progress, Empty | Progress-only edges, as used in this project, could remove text-only choices and accept only progress formats when data is available. This would make existing text-only assignments unsupported. |
| Circles | Text, progress, weighted elements, monochrome/small images, Empty | The project's text/icon-only set is narrower, but would lose progress-only and small-image-only sources. It does not isolate particular health apps. |

The source of the bundled rectangle restriction is `tools/prepare_push_bundle.py`; the legacy standalone XML also supports `LONG_TEXT`. Comparing only `app/src/main/res/raw/watchface.xml` would therefore give the wrong answer for the installed Wear OS 6 forecast face.

For the existing editable weather slot, this project establishes no tighter documented filter that preserves our working image forecast. A genuinely short named menu would require a separate configuration interface for panels we implement, rather than an arbitrary subset of other apps in the normal picker. That would change the previously requested replacement behavior and is not implemented as part of this investigation.

The actionable, smaller change is to consider progress-only edge slots. It is a format restriction, not a guarantee of a particular number or category of menu entries. Installed provider capabilities determine the resulting list.

## Evidence limits and the next decisive check

This archive contains an empty `res/raw/` directory. Its `res/xml/watch_face.xml` is wallpaper metadata, not an exported WFF scene. The authoring file proves its saved settings; it does not establish what a particular WFS release exports or how Samsung's live picker presents it.

If this exact project produces a more selective Large Box menu on the watch, inspect an APK built from it next: compare the compiled manifest, WFF slot attributes, bounds, supported formats and any OEM metadata with our bundled face. A screenshot of that slot's menu would help correlate the exported settings with the actual behavior. No new physical-watch or emulator result is claimed here, and no APK rebuild was needed for this documentation-only checkpoint.
