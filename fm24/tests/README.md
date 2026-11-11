# FM24 tests

```bash
python3 -m unittest discover -s fm24/tests -t .        # from the repository root
```

| Test | Needs | Covers |
|---|---|---|
| `test_layouts.py` | nothing | each decoder in `parse_save.py` on synthetic bytes built from the layout constants |
| `test_live.py` | nothing | save settling, newer-save detection, one job at a time, failure keeps old data, stale-DB rebuild |
| `test_server_fm24.py` | nothing | the explorer in `--game fm24` mode (temporary copy, tiny CSV) |
| `test_fm27_unchanged.py` | git history | FM27 mode API responses equal those of `origin/master` on a synthetic FM27 fixture |
| `test_parse_save.py` | a local save copy | decoding a real save (skipped without `fm24/work/e5/rennes_21dec.fm`) |

`fm27_fixture.py` builds the synthetic FM27 data; `fm27_regression.py` also captures the
UI (page text, requested API paths, screenshots) with the gstack browser for manual checks.
No test reads or writes the FM24 saves folder or touches the game.
