# Add Samsung forecast provider and bundled Wear OS 6 watch face

Samsung's ordinary Weather complication does not supply its native hourly panel. This change adds a replaceable image complication that reads Samsung Weather's saved current/hourly data after a normal user permission grant. It follows the observed favorite-location key, units, rounding, condition mapping and four-hour selection. The whole rectangle opens Samsung Weather; selecting another provider restores that provider's content and action.

A Wear OS 6 host bundles a separately signed resource-only face using Watch Face Push. The original six complication definitions and all touch bounds are preserved. The bundled rectangle's forecast image fills its existing footprint. Missing data stays unavailable, expired data is marked, and bounded timelines handle hour and expiry transitions. Original vector-style weather art is drawn by the provider. No Samsung binaries, artwork or replacement weather service are shipped.

## Validation

- Local APK, test APK, unsigned host test AAB and lint checks pass.
- 28 adapter/reader/timeline JVM tests and 18 layout/data/bundle checks pass.
- Google's pinned official Watch Face Push validator passes all ten checks on the exact signed embedded APK, including WFF and memory.
- The **Samsung forecast preview** workflow adds small/large round Wear OS 6 installation, missing-provider and rendering tests, downloadable builds and screenshots. See the workflow results and [testing guide](SAMSUNG_FORECAST_TESTING.md) for the current evidence.

The user installed the preview on the API 36 Galaxy Watch and confirmed the forecast appears correctly in the face's rectangle and its tap opens Samsung Weather. Replacement, format/refresh edge cases, upgrade persistence and battery/ambient checks remain pending. Stock-emulator fixtures do not establish Samsung integration. The observed OEM interface is not a published stable Samsung API; commercial support and production signing remain release questions. The CI AAB contains a debug-signed embedded face and is a test artifact only.

The GitHub connector currently returns `403 Resource not accessible by integration` when creating a draft PR. This file preserves the review description; no PR has been created by the agent.
