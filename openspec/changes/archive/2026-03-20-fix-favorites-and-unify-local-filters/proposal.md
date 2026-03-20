## Why

The current fallback integration leaks all static 7-11 stores into the favorites selector because favorites are built from the unfiltered 7-11 fallback dataset rather than the user-visible subset. The search/filter interaction is also inconsistent: some controls apply immediately to cached results while others require pressing the search button again, which makes the UI feel unreliable and harder to understand.

## What Changes

- Fix the 7-11 fallback favorites behavior so the favorites list is derived only from the currently scoped, user-visible result set instead of the entire local 7-11 dataset.
- Unify the filtering model so the app fetches by active query scope first, then applies supported refinement filters locally against cached results, with distance increases triggering re-fetches and distance decreases narrowing locally.
- Separate "search inputs" from "local filters" so users can predict which actions re-fetch data and which only refine the current result set.
- Clarify UI behavior around favorites and filters so fallback mode does not expose out-of-scope stores or hidden re-fetch rules.

## Capabilities

### New Capabilities
- `results-filter-interaction`: Consistent local filtering behavior for cached search results, with clear separation between fetch-triggering inputs and local-only filters.

### Modified Capabilities
- `seven-eleven-hybrid-data`: Restrict fallback-derived favorites and visible 7-11 store options to the active search scope instead of the full static store dataset.

## Impact

- Affected code: `app.py` UI event wiring, result caching, filter/favorites derivation, and possibly supporting README notes.
- Affected systems: local Gradio interaction flow and 7-11 fallback result construction.
- Dependencies: existing result-row contract, current cached `results_state`, and current favorites selector behavior.
