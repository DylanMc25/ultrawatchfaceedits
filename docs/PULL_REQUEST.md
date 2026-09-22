# Build Ultra Info Board with an app-selectable bottom rectangle

Create a resource-only WFF 2 Galaxy Watch face with large stacked time, three staggered circles, two edge indicators, a bottom shortcut and an editable rectangular complication. The rectangle accepts installed providers' text, images and progress data; taps go to the selected provider. Samsung Weather's public service is the preferred default with an empty fallback. The blue face switches to black, thin time/date in always-on mode.

The native forecast experiment reported unavailable weather on the physical Galaxy Watch even though Samsung Weather had a forecast. The current implementation uses standard complications to support the requested app selection. Samsung's public Weather sends current conditions, not Info Brick's private hourly chart. The face uses original artwork and no backend, companion app or Samsung-private data access.

The six existing slot IDs and geometry are preserved; slot 7 replaces the former fixed panel menu. A previous panel-menu choice does not map to a provider assignment. The rectangle has no heavy background and supports short/long text, images, ranged/goal progress and weighted elements.

## Validation

Current build, native emulator results and remaining physical checks are recorded in [VALIDATION.md](VALIDATION.md). Regression checks include non-overlapping tap regions, provider-owned data/actions, empty text, progress boundaries and ambient behavior. Emulators exercise all seven choosers and an assigned provider at three positions across the rectangle. Samsung data and real app destinations require a physical-watch test.

![Illustrative provider layout](https://raw.githubusercontent.com/DylanMc25/ultrawatchfaceedits/codex/watchface-redesign/docs/previews/active-illustrative.png)

This preview uses sample data; it is not a native screenshot. Release signing, final package identity, store materials and physical battery/ambient tests remain release prerequisites.
