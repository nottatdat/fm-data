# E7 — Detecting a running FM24

**Method:** checked processes with FM24 closed (start of session) and open (launched via
the Epic launcher, Rennes career loaded).

**Result:** the game runs as `/Users/Shared/Epic Games/FootballManager24/fm.app/Contents/MacOS/fm`
(parent: launchd), process name `fm`. `pgrep -x fm` prints a pid when open and nothing when
closed. The command line contains Epic auth arguments: never log or display it.

**Verdict:** PASS. Use `pgrep -x fm` (exit status only).
