# fm24-player-details Specification

## Purpose
Fills the FM24 player CSV with contract, physical, valuation and personality details
decoded from the save, so the explorer profile shows them instead of blanks.

## Requirements

### Requirement: Height
The extractor SHALL write each player's height in centimetres to the `height` column.

#### Scenario: Height matches the profile
- **WHEN** a player's height in the CSV is compared with their in-game profile
- **THEN** the values are equal

### Requirement: Contract wage and expiry
The extractor SHALL write the weekly wage (in the game's displayed currency) to `wage` and
the contract end date to `expires` for players under contract, and leave both blank for
free agents.

#### Scenario: Contract matches the contract screen
- **WHEN** a contracted player's `wage` and `expires` are compared with their in-game contract
- **THEN** the expiry date is equal and the wage equals the displayed wage within FM's display rounding

#### Scenario: Free agent
- **WHEN** a player has no club
- **THEN** `wage` and `expires` are blank

### Requirement: Stored base valuation
The extractor SHALL write the player's stored base valuation in £ to `value` (blank when
none is stored) and list it as unverified, because FM adjusts it before displaying a range.

#### Scenario: Valuation exported
- **WHEN** a player has a stored valuation
- **THEN** `value` holds it in £ and the extraction metadata lists `value` as unverified

#### Scenario: Valuation shown in the explorer
- **WHEN** a profile or search card shows `value`
- **THEN** it carries the "unverified" marker

### Requirement: Personality attributes
The extractor SHALL write the 8 hidden personality attributes (adaptability, ambition,
loyalty, pressure, professionalism, sportsmanship, temperament, controversy) on a 1–20
scale, listed as unverified in the extraction metadata.

#### Scenario: Personality decoded
- **WHEN** personality attributes are written for a player
- **THEN** each is 1–20 and the metadata lists them as unverified

### Requirement: Undecodable details stay blank
A detail that cannot be located for a player SHALL be left blank rather than taken from a
neighbouring record.

#### Scenario: Record missing
- **WHEN** a player's contract or physical record cannot be found
- **THEN** the corresponding columns are blank and the rest of the row is unaffected
