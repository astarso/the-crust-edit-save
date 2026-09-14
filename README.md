# the-crust-edit-save

Offline save editor for [The Crust](https://store.steampowered.com/app/1465470/),
a UE 4.27 single-player game. Its save files are sequences of zlib chunks with
no checksum, so values can be patched directly. The tool currently edits
credits; other fields are planned (see [Roadmap](#roadmap)).

> **Disclaimer.** Built for fun and to poke at how a UE4 save format works.
> Cheating is bad: at least let the game beat you once before editing its
> numbers. 😉 Single-player offline saves only.

## Requirements

- Python 3.8+, standard library only
- The game fully closed while patching
- Steam Cloud disabled for the game, or Steam offline, otherwise the cloud
  can re-upload the old save over your edit

## Usage

```bash
# print the current credits balance of a slot
python3 the-crust-edit-save.py "<SaveGames>/NEW_ASTA" --detect

# set credits (backs up the original to Level.sav.bak on first run)
python3 the-crust-edit-save.py "<SaveGames>/NEW_ASTA" 58546424
```

`<SaveGames>` is the game's save directory:

| Platform         | Path |
|------------------|------|
| Windows          | `%LOCALAPPDATA%\TheCrust\Saved\SaveGames` |
| Linux (Proton)   | `<steamlibs>/steamapps/compatdata/1465470/pfx/drive_c/users/steamuser/AppData/Local/TheCrust/Saved/SaveGames` |

Any slot folder works: a named save (`NEW_ASTA`), the `sas` quick-save, or an
`Autosave_N_*D_*` folder. The value is stored as float32, so integers above
16 777 216 lose precision; pick a float32-exact number if that matters.

## How it works

1. Reads the live balance from the tail of the `PlayerCredits` or
   `GeneralCredits` series in `Stats.bin` (float32 records with UTF-16 keys).
2. Decompresses every chunk of `Level.sav` and keeps only the occurrences of
   that float whose nearest preceding property tag is `FloatProperty`. This
   skips coincidental matches such as sequential int32 grid indices.
3. Patches all of them, recompresses, rebuilds each 48-byte chunk header
   (`c1832a9e` magic plus duplicated u64 compressed/decompressed sizes), and
   verifies the result parses back cleanly.

`Stats.bin` is an append-only statistics history for the in-game charts. It
is read for detection only and never modified; the game appends the new
balance on its own.

## Rollback

```bash
cd <SaveGames>/NEW_ASTA
mv Level.sav.bak Level.sav
```

The backup is written once, before the first patch of that slot, and is never
overwritten by later runs.

## Roadmap

- Other resources (`Regolith`, `IronOxide`, research points, `Drone`,
  `Colonist`): same FloatProperty patching, values sourced from `Stats.bin`
- `Slot.sav` run parameters: `StartCredits`, `StartRobots`, `MainDifficulty`,
  `EventFrequency`, price and reputation multipliers
- `Player.sav` flags: `LastGameSpeed`, `IsEasyDebugUnlocked`
- `<slot>_TTS.sav`: `UnlockedTechnologies` (add or remove research)
- `DataRegistry.sav`: `TagName` to `BaseValue`/`Additives`/`Multipliers`
  balance constants
- Structural GVAS edits (array counters, string lengths) for size-changing
  operations; today only equal-length float replacement is performed

## License

Apache-2.0, see [LICENSE](LICENSE). Not affiliated with the developer of
The Crust.
