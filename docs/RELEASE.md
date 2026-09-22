# Before selling on Google Play

This repository produces a development build, not a signed production submission.

- Choose the permanent application ID, publisher identity, store name and versioning; remove `com.example` before first publication.
- Reproduce/investigate the API 34 post-editor partial-background redraw captured in the previous validation run (not reproduced in the latest run); confirm stable repainting after provider changes and minute transitions on Galaxy Watch.
- Test on physical Galaxy Watch hardware, including a smaller round model: readable digits, every tap area, complication editor, health consent, provider launch actions, weather/location setup, and background/always-on transitions.
- Exercise real providers for short text (with and without icons/titles), images, ranged values, goals exceeded, and weighted elements. Check unavailable/no-permission and empty states. Samsung-specific data availability must be verified on-device.
- Verify Bottom rectangle can select Samsung Weather and other compatible installed providers; check real data, provider units, unavailable states and whole-area provider-owned taps. Samsung's public provider supplies current conditions, not Info Brick's private hourly chart.
- Verify image/chart providers fit the rectangle without distortion or clipping. Check selection persistence, empty state and consistently signed upgrades preserving IDs 1–6. The removed 0.1.5 Bottom panel menu choice does not map to a provider assignment.
- Inspect long localized month/day strings, temperature extremes, large step counts, 12/24-hour time, and settings persistence after updates.
- Measure active/ambient memory with Google's current tools, actual ambient lit-pixel ratio (under 15%), and real battery consumption. A static preview cannot establish battery behavior.
- Add final icon, store screenshots from the real rendered face, description and pricing; verify current Wear OS Play requirements and complete the Play Console questionnaires.
- Configure private release signing / Play App Signing outside Git. Never commit keys or passwords. Increment `versionCode` for every upload.
- Run internal/closed testing as required by the developer account before submitting for sale.

References: [WFF setup](https://developer.android.com/training/wearables/wff/setup), [ambient requirements](https://developer.android.com/training/wearables/wff/ambient), [Play target requirements](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en-AU).
