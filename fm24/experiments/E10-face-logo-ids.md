# E10 — Face / logo ids in FM24 mode

**Question:** can the explorer's local face/logo packs (keyed by FM person/club id) be
used for FM24 players?

**Method:** looked for packs on the FM24 Mac: `fm27/explorer/assets/` (gitignored),
`~/Documents/Sports Interactive/` and the FM24 user data directory
(`~/Library/Application Support/Sports Interactive/Football Manager 2024/`).

**Result:**
- No face or logo packs exist anywhere on this machine; FM24 has no `graphics` folder.
- The explorer already degrades gracefully: missing images return 404 and the UI removes
  the `<img>` (`onerror`), as seen in E9.
- Id validity cannot be tested without packs and decoded FM24 ids. Real players usually
  keep their unique id across FM versions, but regens/newgens get ids that may collide with
  a different person in an FM27-era pack, and the explorer's club-logo lookup goes through
  FM27 history (`player_club_id`), which is wrong for FM24 by construction.

**Verdict:** PASS (decision recorded). In FM24 mode:
- club logos from FM27 history are disabled (already in design D5);
- faces and logos are not served from FM27 packs; the UI shows its existing
  no-image placeholder. Revisit only if the user installs FM24-era packs.
