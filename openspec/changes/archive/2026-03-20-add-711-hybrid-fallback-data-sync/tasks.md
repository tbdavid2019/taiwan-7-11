## 1. Local 7-11 Fallback Data

- [x] 1.1 Add a project-owned location for normalized 7-11 fallback data and any refresh metadata files.
- [x] 1.2 Implement a refresh script that downloads `s_data.json` and `stores.yaml`, normalizes records by store ID, and writes deterministic local output.
- [x] 1.3 Record provenance metadata such as source URLs, refresh time, and normalized record counts.

## 2. Hybrid 7-11 Runtime Flow

- [x] 2.1 Add app-side loading utilities for the normalized local 7-11 fallback dataset.
- [x] 2.2 Update the 7-11 search flow to attempt live OpenPoint inventory first and fall back to local static nearby-store search on token/API failure.
- [x] 2.3 Extend result rows with source-aware metadata needed to distinguish live inventory rows from static fallback rows.

## 3. UI And Filter Behavior

- [x] 3.1 Update summary or results messaging so users can see when 7-11 is running in fallback mode.
- [x] 3.2 Ensure fallback rows render through the existing table and favorites flow without a separate UI path.
- [x] 3.3 Adjust filter behavior so fallback rows are handled intentionally, especially when the stock-only filter is enabled.

## 4. Documentation And Verification

- [x] 4.1 Update `README.md` with the upstream 7-11 source links and the local refresh workflow.
- [x] 4.2 Verify the live-success path still shows 7-11 expiring-food results when the OpenPoint API is healthy.
- [x] 4.3 Verify the live-failure path still shows nearby 7-11 fallback stores and clear fallback messaging when `MID_V` is expired.
