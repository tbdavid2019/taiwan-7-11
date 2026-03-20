## MODIFIED Requirements

### Requirement: Fallback 7-11 rows SHALL remain compatible with the current results UI
The system SHALL map fallback 7-11 stores into the same result-row structure used by the current UI so that rendering, favorites, and store grouping continue to function without a separate fallback-specific results surface. Any selector or store-choice UI derived from fallback rows SHALL be limited to the active scoped result set rather than the entire local fallback dataset.

#### Scenario: Fallback rows are rendered in the existing table
- **WHEN** the 7-11 fallback path is used
- **THEN** the results payload includes `store_type`, `store_id`, `store_key`, `store_name`, `store_label`, `distance_m`, `item_label`, `qty`, and `tags` fields for each fallback row

#### Scenario: Fallback rows preserve stable store identity
- **WHEN** a user marks a fallback 7-11 store as a favorite
- **THEN** the favorite key remains stable because the fallback row uses the 7-11 store ID as the store identifier

#### Scenario: Favorites do not expose all fallback stores
- **WHEN** the 7-11 fallback path is active and the local fallback dataset contains stores outside the active search scope
- **THEN** the favorites selector shows only fallback stores from the active scoped result set instead of all fallback stores in Taiwan
