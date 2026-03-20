## 1. Scoped Results And Favorites

- [x] 1.1 Define and implement a single scoped-results path that represents the active search scope before secondary display filters are applied.
- [x] 1.2 Update favorites choice generation so it uses the active scoped result set instead of raw fallback rows.
- [x] 1.3 Verify that fallback mode no longer exposes all Taiwan 7-11 stores in the favorites selector.

## 2. Unified Filter Interaction

- [x] 2.1 Classify current controls into fetch-triggering query inputs versus local refinement filters.
- [x] 2.2 Implement asymmetric distance behavior: increasing radius re-fetches, decreasing radius narrows locally from cached results.
- [x] 2.3 Rewire local refinement controls so they consistently update the UI from cached results without requiring another search button press.
- [x] 2.4 Preserve explicit fetch behavior for true query changes such as address, GPS, or input mode changes.

## 3. UI Clarity And Verification

- [x] 3.1 Adjust UI copy or control grouping so users can understand which controls search and which controls only filter.
- [x] 3.2 Verify that live 7-11, fallback 7-11, and FamilyMart results all remain compatible with the new scoped filtering behavior.
- [x] 3.3 Verify favorites-only, stock-only, brand, and tag filters all behave consistently after one search fetch.
- [x] 3.4 Verify that distance decreases use cached results while distance increases trigger a fresh fetch.
