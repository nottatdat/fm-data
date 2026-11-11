# Spec Delta

## Purpose

Lets the Profiles Explorer serve one game's dataset per run, chosen at startup, while
keeping each game's data isolated and the existing FM27 behaviour unchanged.

## ADDED Requirements

### Requirement: Game selection at startup
The explorer SHALL accept a startup option selecting the game dataset, with `fm27` as the
default and `fm24` as the only other accepted value.

#### Scenario: FM24 selected
- **WHEN** the explorer is started with the FM24 option and an FM24 CSV exists
- **THEN** it serves players from the FM24 dataset

#### Scenario: FM24 selected before any extraction
- **WHEN** the explorer is started with the FM24 option and no FM24 CSV exists
- **THEN** it exits non-zero with a message telling the user to run the FM24 save extractor first

#### Scenario: Unknown game
- **WHEN** the explorer is started with an unsupported game value
- **THEN** it exits non-zero listing the accepted values

### Requirement: Default behaviour unchanged
Started without the game option, the explorer SHALL behave exactly as before this change:
same source CSV, same database file, same API responses, same panels and same page content.

#### Scenario: API regression check
- **WHEN** the explorer is started with no game option on the regression fixture
- **THEN** a fixed set of search, filter and profile requests returns responses identical to the pre-change baseline

#### Scenario: UI regression check
- **WHEN** a player profile and the search page are opened with no game option
- **THEN** they show the same panels, labels and content as the pre-change baseline, and no save-freshness banner or polling appears

### Requirement: Per-game data isolation
Each game SHALL use its own database file; building or reloading one game's data SHALL
NOT read, modify or delete another game's database or CSVs.

#### Scenario: FM24 reload leaves FM27 intact
- **WHEN** the FM24 dataset is built or reloaded
- **THEN** the FM27 database and FM27 CSV files have unchanged contents and modification times

### Requirement: No cross-game data in FM24 mode
In FM24 mode the explorer SHALL NOT use FM27-only data sources: career history, Sofascore
form and history-derived club logos SHALL be hidden instead of shown empty, wrong or failing.

#### Scenario: Profile in FM24 mode
- **WHEN** a player profile is opened in FM24 mode while an FM27 history database exists locally
- **THEN** no career-history or Sofascore panel is shown, no club logo is taken from FM27 history, and no request for them fails

### Requirement: Game label
The page title and header SHALL name the game being served instead of a hardcoded FM27
label in FM24 mode.

#### Scenario: Header in FM24 mode
- **WHEN** the explorer runs in FM24 mode
- **THEN** the title and header show FM24 and the player count of the FM24 dataset
