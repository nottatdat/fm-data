# Design

## Context

See proposal.md. Builds on `fm24/save/parse_save.py`: persons, player headers and ratings
records are located; layouts are named constants tied to E-notes. A probe (8 players,
fixed offsets ±6 KB from the person record or header) found no consistent position for
height or wage, and contract expiry for only 2 of 8, so these fields live in records of
their own or vary in position.

## Goals / Non-Goals

**Goals:** each field backed by an experiment with ground truth; decoders follow the
existing pattern (layout constants + one decode function + coverage counted in metadata).

**Non-Goals:** exact market value (FM shows a range), any explorer change.

## Decisions

### D1. Experiment per field group, same method as before
E12 height/weight, E13 contract (wage + expiry), E14 market value, E15 personality. Ground
truth: the 8 profile screenshots (height, weight, value range, personality label) plus one
contract-tab screenshot per player. Search strategies, in order: values near the anchors
already decoded (person record, header, ratings record); records keyed by the player's uid
or person index; whole-block pattern search across the 8 players with a consistent
relative offset. Wage is tried as weekly/monthly/yearly and in GBP/EUR units.

### D2. Linking rule
A detail is accepted only through an explicit link (shared uid/person index, or a fixed
offset inside the same record verified on all ground-truth players). Proximity alone is
not enough: this avoids the misassignment class fixed in the previous change.

### D3. Verification status
Height, wage and expiry are "exact" (visible in FM). Value and personality are listed
under `columns.unverified`, so the explorer shows its "?" marker without code changes.

## Risks / Trade-offs

- [Contract records not linkable] → leave wage/expiry blank (spec allows), document.
- [Wage stored in another currency] → derive the factor from the 8 players and record it.
- [Time] → each experiment is time-boxed (½ day); a failed one is reported, not stretched.
