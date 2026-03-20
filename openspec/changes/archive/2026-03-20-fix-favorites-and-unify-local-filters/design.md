## Context

The app currently caches fetched result rows and already applies several controls locally through `apply_filters()`, but its interaction model is not fully coherent. The search button still acts as the gateway for some meaningful state changes, while other controls update immediately from cached results. This inconsistency makes it difficult for users to know whether changing a control will re-fetch data or simply refine what is already on screen.

The recent 7-11 fallback integration also exposed a scope bug: fallback rows are generated from the full local static dataset, and the favorites selector is built from raw results before the display filters are applied. As a result, the favorites list can show all Taiwan 7-11 stores instead of only the stores relevant to the active search and current visible scope.

Constraints:
- Keep the current Gradio architecture and `results_state`-based local filtering model rather than replacing the whole page flow.
- Preserve one explicit fetch action for location/address searches because changing the location or input mode legitimately requires fresh data.
- Avoid rebuilding favorites from hidden or out-of-scope rows.

## Goals / Non-Goals

**Goals:**
- Ensure favorites choices reflect only the currently scoped result set rather than all raw fallback rows.
- Define a consistent contract: search inputs trigger fetches, local filters only refine the cached result set.
- Make the UI behavior predictable so users do not have to guess when another click is required.
- Preserve compatibility with existing live/fallback row structures and favorites persistence.

**Non-Goals:**
- Introducing background auto-refresh of live store data when location inputs change.
- Replacing the search button with fully automatic network fetching on every control change.
- Redesigning the whole UI layout beyond the minimum needed to clarify behavior.

## Decisions

### 1. Treat fetch inputs and local filters as two distinct layers

The app will keep one explicit fetch operation for changing address, GPS, or other true query inputs. Distance is a hybrid case: increasing the radius requires a fresh fetch because the cache may not contain the newly expanded band, while decreasing the radius should narrow locally from cached results.

Rationale:
- Location changes genuinely require network work and should remain explicit.
- Every refinement control using cached data should behave immediately and consistently.
- Radius expansion cannot be satisfied from a narrower cached result set, but radius reduction can.

Alternatives considered:
- Re-fetch on every control change: rejected because it is slower, harder to reason about, and unnecessary for purely local filters.
- Keep the mixed model: rejected because that is the current source of confusion.

### 2. Build favorites choices from the filtered, in-scope store set

The favorites selector should be derived from the same scoped rows the user can currently act upon, not from raw pre-filter rows.

Rationale:
- A favorites list is a UI affordance tied to visible or meaningful choices, not a backdoor into hidden data.
- This fixes the all-Taiwan 7-11 fallback leak without needing to discard the local fallback dataset itself.

Alternatives considered:
- Keep building favorites from raw rows and hope display filters hide the problem: rejected because it breaks trust in the UI.
- Hard-cap fallback rows before caching without preserving full search results: rejected because it would blur the boundary between cached search scope and display filters.

### 3. Define a stable "search scope" before secondary filters are applied

The app should derive an initial result scope from the active search action and any query-defining inputs, then apply secondary filters like stock-only, favorites-only, and tag filters on top of that scope.

Rationale:
- This prevents downstream UI artifacts such as favorites lists from pulling in stores outside the active search radius or query context.
- It provides a clean mental model for both implementation and user behavior.

Alternatives considered:
- Let every consumer decide its own subset ad hoc: rejected because it creates drift between the table, summary, and favorites selector.

## Risks / Trade-offs

- [Separating fetch inputs from local filters may require minor event rewiring] -> Keep the explicit search button and only move clearly local controls onto cached filtering paths.
- [Users may expect some controls to re-fetch even when they now act locally] -> Clarify the interaction in UI copy or control grouping.
- [Favorites scoped too aggressively could hide previously saved stores outside the current search] -> Preserve stored favorite IDs, but only show selectable choices relevant to the current scoped result set.

## Migration Plan

1. Define and implement a single scoped-results derivation path, including radius-expansion re-fetch behavior and radius-reduction local narrowing.
2. Use that scoped path for table rendering, summary generation, and favorites choices.
3. Rewire UI controls so local filters always operate on cached results and fetch-triggering inputs remain explicit.
4. Verify fallback and live paths both produce correct favorites and predictable filter behavior.

## Open Questions

- Whether the UI should visually separate "搜尋條件" and "顯示篩選" sections to make the behavior obvious.
