# Spec Delta

## Purpose

Turns a Football Manager 24 save file into a local player CSV that the Profiles Explorer
can load, so FM24 careers on macOS can be browsed without reading game memory.

## ADDED Requirements

### Requirement: Default save selection
The extractor SHALL read the most recently modified career `.fm` file in the FM24 macOS
saves directory, excluding FM's `last save overwrite backup*` files, unless the user names
a specific save file.

#### Scenario: No save given
- **WHEN** the extractor runs without a save argument and the saves directory has several career `.fm` files
- **THEN** it reads the one with the newest modification time and reports its file name

#### Scenario: Backup is newest
- **WHEN** a `last save overwrite backup*.fm` file is newer than every career save
- **THEN** the extractor ignores the backup and reads the newest career save

#### Scenario: Explicit save given
- **WHEN** the user passes a path to a specific `.fm` file
- **THEN** the extractor reads that file regardless of modification times or name

#### Scenario: No save available
- **WHEN** no career `.fm` file exists at the default location and none is given
- **THEN** the extractor exits non-zero with a message naming the directory it searched

### Requirement: Player CSV in the shared explorer schema
The extractor SHALL write one row per player to `fm24_players.csv` with every source
column the explorer's player importer reads; any column whose value is not decoded SHALL
be present and blank.

#### Scenario: Partially decoded fields
- **WHEN** the extractor decodes name, DOB, club and visible attributes but not hidden personality attributes
- **THEN** the CSV has every importer source column, with personality columns blank

#### Scenario: Age without a known game date
- **WHEN** the in-game date cannot be decoded
- **THEN** the age column is blank rather than computed from the real-world date

### Requirement: Decoded values match the game
DOB, age, nationality and club SHALL equal what the game shows for the same save.
Attributes and position ratings SHALL come from the player's live attribute block; each
attribute is within ±1 of the on-screen value and equal to it when it shows no change arrow.

#### Scenario: Own player identity compared
- **WHEN** one of the user's own players is looked up in the CSV and on their in-game profile in the same save
- **THEN** DOB, age, nationality and club are equal

#### Scenario: Own player attributes compared
- **WHEN** that player's attributes are compared with the profile screen
- **THEN** each differs by at most 1, and attributes without a change arrow are equal

### Requirement: Unverified fields marked
Fields the game does not show numerically (CA, PA, hidden attributes) SHALL be listed as
unverified in the extraction metadata.

#### Scenario: CA/PA exported
- **WHEN** CA and PA are decoded and written to the CSV
- **THEN** the extraction metadata lists `ca` and `pa` as unverified

#### Scenario: Hidden attributes exported
- **WHEN** hidden attributes (consistency, important matches, injury proneness, versatility, dirtiness) are written to the CSV
- **THEN** the extraction metadata lists them as unverified

### Requirement: Read-only and game-independent
The extractor SHALL never modify the save file and SHALL NOT interact with the running game process.

#### Scenario: Extraction while FM is running
- **WHEN** the extractor runs while FM24 is open
- **THEN** the save file's bytes and modification time are unchanged and the game is not signalled, injected or automated

### Requirement: Extraction provenance
Each extraction SHALL record the save file name, its saved-at time (file modification
time) and, when decodable, the in-game date, alongside the CSV.

#### Scenario: Provenance recorded
- **WHEN** an extraction completes
- **THEN** a metadata record next to the CSV states the save file, saved-at time, and in-game date or that it is unknown

### Requirement: Consistent snapshot
The extractor SHALL NOT produce output from a save that is still being written.

#### Scenario: Save in progress
- **WHEN** the save file changes size or modification time during extraction
- **THEN** the extractor discards the partial result and reports that the save was still being written

### Requirement: Atomic publish
The CSV and its metadata SHALL be replaced only together and only after a complete,
successful extraction; a failed run SHALL leave the previous CSV and metadata intact.

#### Scenario: Extraction fails midway
- **WHEN** an extraction fails after it started writing output
- **THEN** the previous CSV and metadata are unchanged and still describe each other

### Requirement: Local data only
Generated FM24 CSVs, metadata and intermediate files SHALL stay out of version control.

#### Scenario: After an extraction
- **WHEN** `git status` is run after an extraction
- **THEN** no generated FM24 data file appears as untracked or modified
