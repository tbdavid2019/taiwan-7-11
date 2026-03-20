## Why

The current 7-11 experience depends entirely on the OpenPoint `MID_V` token flow, which now returns an expired-credential error and makes 7-11 results disappear even when nearby stores still exist. The project needs a durable fallback so users can still browse nearby 7-11 locations, and it also needs a repeatable way to refresh local store data plus clear source attribution in the documentation.

## What Changes

- Add a hybrid 7-11 store data flow that prefers the existing live OpenPoint API for expiring-food results and falls back to local static 7-11 store data when the live token or API is unavailable.
- Add a local 7-11 data update script that fetches and normalizes upstream store datasets into a project-owned file used by the fallback flow.
- Surface fallback state in the UI so users can distinguish live expiring-food results from static store-location results.
- Document the upstream 7-11 data sources and the local refresh workflow in `README.md`.

## Capabilities

### New Capabilities
- `seven-eleven-hybrid-data`: Hybrid 7-11 store discovery that combines live OpenPoint expiring-food data with static fallback store-location data.
- `store-data-refresh`: Local refresh workflow for pulling upstream 7-11 datasets, normalizing them, and storing project-ready data with source attribution.

### Modified Capabilities
- None.

## Impact

- Affected code: `app.py`, `README.md`, and new local data-refresh assets/scripts.
- Affected systems: 7-11 OpenPoint live API, static upstream GitHub-hosted store datasets, local normalized data files.
- Dependencies: local parsing/normalization logic for remote JSON/YAML inputs, distance calculation against fallback coordinates, and update-time metadata for documentation/runtime messaging.
