## Context

The current application queries 7-11 inventory only through the OpenPoint LoveFood API and requires a valid `MID_V` to acquire a token before fetching nearby stores and store details. That dependency is brittle: once `MID_V` expires, all 7-11 results disappear even though the app can still determine the user's coordinates and still fetch FamilyMart data.

The proposed change adds a second 7-11 data path based on static store metadata pulled from publicly available upstream datasets. One upstream source (`s_data.json` from `taiwan-cvs-map`) includes store coordinates and is suitable for fallback proximity search. Another (`stores.yaml`) provides a lighter-weight store-number-to-name/address mapping and can be used as a supplementary verification source during normalization. The app also needs a documented refresh workflow so the local fallback dataset does not drift indefinitely.

Constraints:
- The existing Gradio UI and filtering model should remain largely intact.
- Fallback data must fit the app's current result row shape so favorites, filtering, and rendering continue to work.
- Users must be able to distinguish live expiring-food data from static fallback store listings.

## Goals / Non-Goals

**Goals:**
- Preserve 7-11 visibility when the live OpenPoint token flow fails.
- Use a local normalized dataset as the fallback source so the app does not depend on a remote GitHub fetch at request time.
- Add a refresh script that can re-download upstream 7-11 datasets and rebuild the local fallback file.
- Document all upstream sources and the local refresh workflow in `README.md`.
- Keep the result contract compatible with existing filtering, favorites, and table rendering.

**Non-Goals:**
- Replacing the live OpenPoint inventory flow when it is healthy.
- Reconstructing 7-11 expiring-food inventory from static sources.
- Building a general ETL framework for every convenience-store provider.
- Solving automatic `MID_V` extraction from OpenPoint traffic.

## Decisions

### 1. Use a local normalized 7-11 fallback dataset derived primarily from `s_data.json`

The fallback source will be a checked-in project data file produced by a refresh script. The script will fetch:
- `s_data.json` as the primary source because it includes `id`, `name`, `address`, `lat`, and `lng`
- `stores.yaml` as a supplemental source for store-number/address cross-checking

Rationale:
- `s_data.json` is immediately usable for radius-based search because it contains coordinates.
- Keeping a normalized local file avoids runtime dependence on GitHub availability.
- Using `stores.yaml` as a secondary source gives the project an additional attribution trail and a way to enrich or sanity-check normalized rows.

Alternatives considered:
- Use `stores.yaml` directly at runtime: rejected because it lacks coordinates.
- Fetch remote JSON on every user search: rejected because it adds latency and another runtime dependency.

### 2. Keep a single result-row contract and encode fallback rows as zero-inventory store entries

Fallback 7-11 rows will be transformed into the same structure used by the existing UI. They will set:
- `item_label` to a static-data message
- `qty` to `0`
- `tags` to `[]`

Rationale:
- This minimizes UI churn and avoids duplicating the rendering/filtering pipeline.
- Existing favorites and store grouping logic already key off `store_type` and `store_id`, which also works for static rows.

Alternatives considered:
- Add a separate 7-11 fallback table: rejected because it fragments the UX and duplicates filtering logic.
- Introduce a radically different data model: rejected because it would force a broader refactor than the problem requires.

### 3. Add explicit source-state metadata so filters and messaging can treat fallback rows differently

Normalized rows should carry enough metadata to tell whether they came from live inventory or static fallback data, such as `data_source` and a short status note. The UI summary and/or results area should show when 7-11 is running in fallback mode.

Rationale:
- Users must not interpret fallback store listings as live inventory results.
- The app can choose not to hide static fallback rows merely because `qty == 0` when `only_in_stock` is enabled.

Alternatives considered:
- Reuse `qty == 0` as the only signal: rejected because it is ambiguous and interacts poorly with the existing stock filter.

### 4. Put refresh logic in a dedicated script with deterministic outputs

The refresh workflow will live in a dedicated script under the repository and produce project-owned data files plus metadata such as refresh timestamp and record counts.

Rationale:
- A script is the simplest repeatable unit for future manual or scheduled updates.
- Deterministic outputs make repository diffs reviewable and suitable for future automation.

Alternatives considered:
- Manual copy/paste updates: rejected because they are error-prone and undocumented.
- Pulling data only through the upstream TypeScript script: rejected because the app only needs normalized outputs, not a dependency on another repo's tooling.

## Risks / Trade-offs

- [Fallback rows may be hidden by the existing "only in stock" filter] -> Add row/source metadata and adjust filter behavior so fallback visibility is intentional rather than accidental.
- [Upstream static datasets may drift or disagree on store naming/address details] -> Normalize around store ID, preserve source metadata, and optionally use `stores.yaml` as a verification input rather than a hard override.
- [Local fallback data may become stale] -> Store refresh timestamps and document the update script in `README.md`.
- [Users may confuse static store listings for live inventory] -> Render a clear fallback notice and distinct item label text for static rows.

## Migration Plan

1. Add the local normalized 7-11 data file and refresh script.
2. Update the app data-loading path so 7-11 live requests fall back to local static store search on token/API failure.
3. Add UI messaging and filter adjustments for fallback rows.
4. Update `README.md` with data sources and refresh instructions.
5. Verify live-success and live-failure paths produce understandable results.

Rollback is straightforward: remove the fallback path and revert to the current live-only OpenPoint integration, though that would also restore the existing outage behavior when `MID_V` expires.

## Open Questions

- Whether the normalized fallback data should be committed under `data/` or another project-specific location.
- Whether the refresh script should fail hard on source mismatch between `s_data.json` and `stores.yaml` or merely emit warnings.
- Whether fallback rows should remain visible when "only in stock" is enabled, or whether the UI should automatically relax that filter with a warning.
