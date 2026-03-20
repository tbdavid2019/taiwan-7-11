## ADDED Requirements

### Requirement: The project SHALL provide a repeatable local 7-11 data refresh workflow
The system SHALL include a script or command that downloads the upstream 7-11 static store sources, normalizes them into a project-owned fallback dataset, and writes the refreshed data to the repository for runtime use.

#### Scenario: Refresh succeeds
- **WHEN** a maintainer runs the refresh workflow with network access
- **THEN** the workflow downloads the configured upstream source files and writes a normalized local 7-11 fallback dataset for the app

#### Scenario: Refresh output is deterministic
- **WHEN** the upstream source content has not changed
- **THEN** repeated refresh runs produce the same normalized store records except for explicitly tracked refresh metadata

### Requirement: The refresh workflow SHALL track source provenance and refresh metadata
The system SHALL preserve enough metadata to identify where the local fallback dataset came from and when it was last refreshed.

#### Scenario: Source provenance is stored
- **WHEN** the refresh workflow writes the local fallback dataset
- **THEN** it records the upstream source URLs or equivalent provenance metadata used to build that dataset

#### Scenario: Refresh metadata is available
- **WHEN** the refresh workflow completes successfully
- **THEN** it records refresh time and record counts for the normalized dataset

### Requirement: The refresh workflow SHALL support multiple upstream inputs
The system SHALL support `s_data.json` as the primary 7-11 fallback source and `stores.yaml` as a supplementary source for normalization or verification.

#### Scenario: Primary source provides coordinates
- **WHEN** the refresh workflow processes `s_data.json`
- **THEN** the normalized output includes store coordinates suitable for nearby-store distance calculations

#### Scenario: Supplementary source can enrich or validate data
- **WHEN** the refresh workflow processes `stores.yaml`
- **THEN** it uses store IDs and address/name information as supplementary data without requiring `stores.yaml` to replace the primary coordinate-bearing source

### Requirement: Project documentation SHALL cite upstream 7-11 sources and refresh usage
The system SHALL document the upstream source URLs, repository references, and the local refresh workflow in `README.md`.

#### Scenario: README lists upstream sources
- **WHEN** a maintainer reads the project README
- **THEN** the README lists the configured 7-11 upstream datasets and repository/script references used by the local refresh workflow

#### Scenario: README explains refresh execution
- **WHEN** a maintainer wants to update local 7-11 fallback data
- **THEN** the README explains which command or script to run and what local files it updates
