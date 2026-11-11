# Proposal

## Why

The FM24 save extractor (change `fm24-macos-save-explorer`) leaves height, weight, wage,
contract expiry, market value and personality blank, so the explorer's profile shows "—"
for facts the user looks at every day. A quick probe showed they are not at fixed offsets
from the records decoded so far, so they need the same experiment-first treatment.

## What Changes

- Experiments, one per field group, each time-boxed with a pass/fail against the user's
  in-game screens (profile screenshots of 8 players already exist; contract-tab screenshots
  to be provided):
  - height and weight,
  - contract: wage and expiry date,
  - market value: not found by E14; a research lead (fm-open-scout) then located FM's
    **stored base valuation** right after the attributes. It is exported as `value`,
    unverified, because FM adjusts it for the displayed range,
  - personality (8 hidden attributes; FM shows only a label, so values stay unverified).
- `fm24/save/parse_save.py` writes the decoded fields into the existing CSV columns
  (`height`, `wage`, `expires`, `value`, the 8 personality columns), with weight added only
  if the explorer can show it without a schema change.
- The explorer needs no change: the profile already shows these columns, and unverified
  ones get the existing "?" marker through the extraction metadata.

Non-goals: role suitability (separate follow-up), asking price, wage demand, transfer
status, FM27 changes.

## Capabilities

### New Capabilities
- `fm24-player-details`: decoding contract, physical and personality details of
  FM24 players from a save into the explorer CSV.

### Modified Capabilities
- None.

The explorer gains only "?" markers for `value` (`static/app.js` tags the market-value
fact with `data-k`; `static/savemode.js` marks it); FM27 output is unchanged.

## Impact

- `fm24/save/parse_save.py` (new layout constants + decoders), `fm24/tests/`,
  `fm24/csv/README.md`, new notes `fm24/experiments/E12..E15`.
- No change to the explorer, FM26/FM27 or `tools/`.
