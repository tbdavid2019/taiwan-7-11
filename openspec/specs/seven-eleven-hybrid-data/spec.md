# seven-eleven-hybrid-data Specification

## Purpose
TBD - created by archiving change add-711-hybrid-fallback-data-sync. Update Purpose after archive.
## Requirements
### Requirement: 7-11 search SHALL fall back to local static store data when live inventory access fails
The system SHALL attempt the existing OpenPoint live 7-11 inventory flow first. If token acquisition or downstream 7-11 API calls fail, the system SHALL search a local normalized 7-11 fallback dataset by user coordinates and return nearby 7-11 stores within the active search radius.

#### Scenario: Live 7-11 inventory succeeds
- **WHEN** the user runs a nearby-store search and the OpenPoint token plus nearby/detail requests succeed
- **THEN** the system returns live 7-11 inventory results using the existing live 7-11 flow

#### Scenario: Live 7-11 token is expired
- **WHEN** the user runs a nearby-store search and the OpenPoint token request fails because the credential is expired or otherwise unusable
- **THEN** the system returns nearby 7-11 stores from the local normalized fallback dataset instead of returning no 7-11 results

#### Scenario: Live 7-11 downstream request fails
- **WHEN** the OpenPoint token request succeeds but nearby-store or store-detail requests fail
- **THEN** the system falls back to the local normalized 7-11 dataset for the 7-11 portion of the response

### Requirement: Fallback 7-11 rows SHALL remain compatible with the current results UI
The system SHALL map fallback 7-11 stores into the same result-row structure used by the current UI so that rendering, favorites, and store grouping continue to function without a separate fallback-specific results surface.

#### Scenario: Fallback rows are rendered in the existing table
- **WHEN** the 7-11 fallback path is used
- **THEN** the results payload includes `store_type`, `store_id`, `store_key`, `store_name`, `store_label`, `distance_m`, `item_label`, `qty`, and `tags` fields for each fallback row

#### Scenario: Fallback rows preserve stable store identity
- **WHEN** a user marks a fallback 7-11 store as a favorite
- **THEN** the favorite key remains stable because the fallback row uses the 7-11 store ID as the store identifier

### Requirement: The UI SHALL disclose when 7-11 results are using fallback data
The system SHALL clearly indicate when 7-11 results are using static fallback data rather than live expiring-food inventory data.

#### Scenario: Fallback notice is shown
- **WHEN** the 7-11 fallback path is used for a search
- **THEN** the UI shows a message that live 7-11 inventory is unavailable and that nearby static 7-11 store data is being displayed

#### Scenario: Fallback item text is explicit
- **WHEN** a fallback 7-11 row is rendered
- **THEN** the row's item label states that the entry is static store data and does not provide live expiring-food inventory

### Requirement: Filters SHALL handle fallback rows intentionally
The system SHALL distinguish fallback 7-11 rows from live inventory rows so that filters do not silently remove all fallback results without user-facing intent.

#### Scenario: Stock filter does not silently erase fallback context
- **WHEN** the 7-11 fallback path is active and the user has enabled the stock-only filter
- **THEN** the system either preserves fallback rows or provides explicit fallback-aware behavior so the user can still understand why 7-11 inventory is unavailable

#### Scenario: Distance and store-brand filters still apply
- **WHEN** fallback 7-11 rows are generated
- **THEN** the configured search radius and store-brand filters are applied consistently to those rows

