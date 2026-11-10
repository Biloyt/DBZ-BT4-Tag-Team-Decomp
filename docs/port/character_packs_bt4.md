# BT4decomp: external character packages (foundation, not a loader yet)

**Status:** package-format proposal and standalone validation tool only. There is **no character ID >= 250 runtime support**, no menu entry and no added-character combat support in this commit. Do **not** copy BT3/PS2 mods into BT4 game files; their layouts and character tables differ.

## Goal

Install an independent character as a separate pack, *without overwriting an existing character*, then allow the runtime to assign an ID and make all related resources available in battle and in the character selector. The current checker is the first, reversible step toward a package loader.

## Proposed format (schema v1)

Place each package under `characters/<folder>/` outside the game archives:

```text
characters/
  sample-mira-clone/
    character.json
    model.pak
    animations.pak
    effects.pak
    portrait.bin          # optional
    member_p1.bin         # optional
    member_p2.bin         # optional
```

Example `character.json`:

```json
{
  "schema_version": 1,
  "name": "Mira Test Clone",
  "base_id": 236,
  "assets": {
    "model": "model.pak",
    "animations": "animations.pak",
    "effects": "effects.pak"
  }
}
```

- `base_id` selects an **existing BT4 character (0–249)** as the fallback for unavailable data in a *future* runtime. It is **not** the added character's new ID.
- `model`, `animations`, and `effects` are required. Optional keys: `member_p1`, `member_p2`, `portrait`, `voice_jp`, `voice_us`.
- Files must be nonempty, with relative paths contained inside that character's folder. The validator computes SHA-256 to track the exact files. It does not parse the internal PAK or prove animation compatibility.
- **No copyrighted game assets belong in this Git repository.** Use local files you are authorized to modify.

## Preflight check (Python 3.10+, standard library)

From the repository root:

```bash
python port/tools/bt4_pack_validator.py --root characters --index character-packs-index.json
python -m unittest discover -s tools/review/tests -p 'test_bt4_pack_validator.py' -v
```

The scanner is read-only on `characters/` and does not read or change `gamedata/` or `gamedata/mods/`. It writes **only** the index path explicitly supplied via `--index` after validation succeeds. The index lists manifest metadata, file sizes and hashes so a future loader can assign IDs deterministically and detect conflicting packs.

## Required runtime work (not yet implemented)

1. Allocate IDs beyond 249 without colliding with sentinel values, common-data tables or other file partitions. Existing `CHRVIEW_CHARA_COUNT` and the `Bt4_CharaFromModelFile` loop currently stop at 250.
2. Integrate package-resource aliases into *both* `port/src/plat_file.c` and `port/src/plat_fcache.c`. The existing `BT3_FILE_ALIAS` hook is not a complete character loader.
3. Adapt costume/model ID mapping, character stats, animations, attack references, effects, AI, voices and battle-member data to the new ID, including safe fallback to `base_id` only where appropriate.
4. Extend the Duel character-select grid beyond its current fixed entry limits, and provide chips/portraits/names/locks. New entries must never delete original roster cells.
5. Test a clone of an existing BT4 character **as its own character** (ID 250), with both original and clone selectable in the same match. Then test an original third-party pack, and finally multiple packs in one run.
6. Verify offline versus, transformation and save/loading paths before allowing network play. Network synchronization must refuse mismatched package inventories.

The BT3 `char-packages` work is a technical reference, not a drop-in solution: https://github.com/z3xox/Tenkaichi3Decomp/tree/char-packages .

**Test setup:** the existing `BT4-Test-236` experiment and its grouped 236–249 roster patch remain separate from the new runtime work. No source change in this foundation touches them.
