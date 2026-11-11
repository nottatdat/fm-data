# Spec Delta

## Purpose

Makes it obvious in the explorer which save the browsed data came from and how stale it
is, and lets the user reload after saving manually in the game.

## ADDED Requirements

### Requirement: Provenance banner
In a save-backed mode the explorer SHALL show the save file name, its saved-at time with
relative age, and the in-game date when known, on every page.

#### Scenario: Data loaded
- **WHEN** the explorer shows FM24 data
- **THEN** a banner shows e.g. `Data from "Career - Rennes.fm", saved 22:08 (14 min ago)`

#### Scenario: In-game date unknown
- **WHEN** the in-game date could not be decoded
- **THEN** the banner shows the saved-at time only and does not show a placeholder date

### Requirement: Unverified values labelled
Values the extraction metadata lists as unverified SHALL be visibly labelled as unverified
wherever the explorer displays them.

#### Scenario: CA/PA on a profile
- **WHEN** a profile shows CA and PA that the metadata lists as unverified
- **THEN** both values carry an "unverified" marker

#### Scenario: Hidden attributes on a profile
- **WHEN** a profile shows hidden attributes that the metadata lists as unverified
- **THEN** they carry an "unverified" marker

### Requirement: Manual-save notice while FM is running
When FM24 is running, the banner SHALL tell the user that data reflects the last save and
to press ⌘S in FM for fresh data; it SHALL NOT trigger a save itself.

#### Scenario: Game open
- **WHEN** the explorer detects a running FM24 process
- **THEN** the banner includes the instruction to press ⌘S in FM, and no input is sent to the game

#### Scenario: Game closed
- **WHEN** no FM24 process is running
- **THEN** the banner shows provenance only, without the ⌘S instruction

### Requirement: Newer save detection
The explorer SHALL detect, without user action and without touching the game, when a
career save newer than the loaded one exists, and offer to load it by name.

#### Scenario: User saved in FM
- **WHEN** the user presses ⌘S in FM and the save finishes writing
- **THEN** within 10 seconds the banner shows `New save detected: "<save name>" (<time>)` with a **Load it** action

#### Scenario: Save still being written
- **WHEN** the newer save file is still changing
- **THEN** the explorer does not offer it until the file has stopped changing

#### Scenario: Only a backup changed
- **WHEN** only a `last save overwrite backup*.fm` file is newer than the loaded save
- **THEN** no newer save is offered

### Requirement: Reload on request
Choosing **Load it** SHALL re-extract the newer save, rebuild the FM24 dataset and refresh
the view, showing progress while it runs and keeping the previous data on failure.

#### Scenario: Successful reload
- **WHEN** the user chooses Load it
- **THEN** a loading state is shown, then the view and banner reflect the new save

#### Scenario: Derived data refreshed
- **WHEN** a reload completes and the new save has a club or division absent from the old one
- **THEN** filters, totals and club search include it without restarting the explorer

#### Scenario: Failed reload
- **WHEN** extraction or rebuild fails
- **THEN** the previous dataset stays browsable, the banner still describes it, and the error reason is shown

#### Scenario: Reload already running
- **WHEN** Load it is chosen while a reload is in progress
- **THEN** no second reload starts and the UI keeps showing the running one's progress
