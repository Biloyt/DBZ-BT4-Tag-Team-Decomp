#!/usr/bin/env python3
"""Apply the small PC-only BT4 ID250 *recognition* patch to repository C sources.

This is preparatory engine code, NOT an independent character, menu or combat pack.
Designed for the build job: it edits the runner's Git checkout, never game files.
"""
from __future__ import annotations
import argparse
from pathlib import Path

OLD_HEADER = '#define CHRVIEW_CHARA_COUNT 250'
NEW_HEADER = '#ifdef PORT\n#define CHRVIEW_CHARA_COUNT 251\n#else\n#define CHRVIEW_CHARA_COUNT 250\n#endif'
OLD_LOOP = 'for (c = 0; c < 250; c++) {'
NEW_LOOP = 'for (c = 0; c < CHRVIEW_CHARA_COUNT; c++) {'
OLD_GRID = '(id >= 0xA5 && id < 250)'
NEW_GRID = '(id >= 0xA5 && id < CHRVIEW_CHARA_COUNT)'
OLD_UNLOCK = '((id) >= 0xA5 && (id) < 250)'
NEW_UNLOCK = '((id) >= 0xA5 && (id) < CHRVIEW_CHARA_COUNT)'


def replace_exact(source: str, old: str, new: str, count: int, filename: str) -> str:
    if new in source and old not in source:
        return source
    if source.count(old) != count:
        raise ValueError(f'{filename}: expected {count} original match(es), found {source.count(old)}')
    return source.replace(old, new)


def header(source: str) -> str:
    if NEW_HEADER in source:
        return source
    return replace_exact(source, OLD_HEADER, NEW_HEADER, 1, 'view_a.h')


def viewer(source: str) -> str:
    return replace_exact(source, OLD_LOOP, NEW_LOOP, 1, 'view_a_d.c')


def grid(source: str) -> str:
    source = replace_exact(source, OLD_GRID, NEW_GRID, 4, 'view_a_e.c cursor')
    source = replace_exact(source, OLD_UNLOCK, NEW_UNLOCK, 1, 'view_a_e.c unlock macro')
    return source


def process(repo: Path, apply: bool) -> int:
    files = {
        repo / 'include/battle/view_a.h': header,
        repo / 'src/battle/view_a_d.c': viewer,
        repo / 'src/battle/view_a_e.c': grid,
    }
    # Stage every replacement in memory before writing anything.
    staged = []
    for path, fn in files.items():
        before = path.read_text(encoding='utf-8')
        after = fn(before)
        staged.append((path, before, after))
    if not apply:
        if any(before != after for _, before, after in staged):
            print('Patch ID250 not applied yet; use --apply in disposable build checkout.')
            return 1
    else:
        for path, before, after in staged:
            if before != after:
                path.write_text(after, encoding='utf-8', newline='')
    for path, before, after in staged:
        status = 'modified' if before != after and apply else 'OK'
        print(f'{path.relative_to(repo)}: {status}')
    print('ID 250 recognized by viewer/menu helpers only. NOT selectable/playable yet.')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    args = ap.add_mutually_exclusive_group(required=True)
    args.add_argument('--apply', action='store_true')
    args.add_argument('--check', action='store_true')
    ap.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    opts = ap.parse_args()
    return process(opts.repo.resolve(), apply=opts.apply)


if __name__ == '__main__':
    raise SystemExit(main())
