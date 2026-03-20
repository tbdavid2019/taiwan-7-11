## ADDED Requirements

### Requirement: The system SHALL use one explicit fetch action and local post-fetch filtering
The system SHALL fetch store data when the user performs an explicit search action for the active query inputs, and it SHALL apply supported refinement filters locally against the cached result set afterward. Distance SHALL behave as a scoped query input when the radius is expanded, and as a local narrowing filter when the radius is reduced.

#### Scenario: Search action fetches data
- **WHEN** the user changes query-defining inputs such as address, GPS coordinates, or input mode and performs a search
- **THEN** the system fetches a fresh result set and stores it as the current cached search results

#### Scenario: Local filters do not require another fetch
- **WHEN** the user changes a local filter after a search has already completed
- **THEN** the system updates the visible results from cached data without requiring another search button press

#### Scenario: Distance increase requires a fresh fetch
- **WHEN** the user increases the search radius beyond the radius used for the current cached result set
- **THEN** the system treats that change as requiring a fresh fetch because the cache may not contain stores from the expanded distance range

#### Scenario: Distance decrease reuses the cached result set
- **WHEN** the user decreases the search radius below the radius used for the current cached result set
- **THEN** the system narrows the visible results locally from cached data without requiring another fetch

### Requirement: The system SHALL distinguish query inputs from local refinement controls
The system SHALL define and implement a clear boundary between controls that change the underlying query scope and controls that only refine display of the current cached results.

#### Scenario: Query input changes do not silently masquerade as local filters
- **WHEN** the user changes a query-defining input
- **THEN** the system treats that change as requiring a fresh search action rather than pretending the cached results already cover the new query

#### Scenario: Distance is handled asymmetrically by cache coverage
- **WHEN** the user changes the distance control
- **THEN** the system re-fetches on radius expansion and filters locally on radius reduction

#### Scenario: Refinement controls behave consistently
- **WHEN** the user changes refinement controls such as stock-only, favorites-only, tag filters, or brand filters
- **THEN** those controls behave consistently as local filters over the cached results

### Requirement: The system SHALL derive favorites choices from the current scoped result set
The system SHALL build the favorites selector from the currently scoped search results rather than from hidden or out-of-scope raw rows.

#### Scenario: Favorites choices match the active scoped results
- **WHEN** the user has completed a search and opens the favorites selector
- **THEN** the selector contains only stores present in the active scoped result set

#### Scenario: Hidden out-of-scope stores are not offered as current favorites choices
- **WHEN** raw fallback or cached data contains stores outside the active scoped result set
- **THEN** those stores are not shown as selectable favorites choices for the current search context
