#!/usr/bin/env python3
"""Opt-in source patch for the BT4decomp PC file-cache alias path.

Fixes the discrepancy where BT3_FILE_ALIAS was honored by Port_FilePath,
but Port_FileOpenHost (used by size/read and fingerprint) did not honor it.
This does NOT add any new character ID, menu slot or combat parameters.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER = "static PortFile *open_rel(const char *rel) {"
WRAPPER = '''/* Resolve the same source-file aliases for the host file cache and the path API.
 * This makes the existing BT3_FILE_ALIAS override apply consistently to all
 * file access, not just direct host path requests. */
int Port_FileAlias(const char *rel, char *out, unsigned size) {
    const char *value;
    if (rel == NULL || out == NULL || size == 0) return 0;
    value = alias_target(rel);
    if (value == NULL || value[0] == '\\0') return 0;
    snprintf(out, (size_t)size, "%s", value);
    return 1;
}

'''
OLD_CALL = 'if (PortStages_Alias(rel, target, (unsigned)sizeof(target)) || PortSongs_Alias(rel, target, (unsigned)sizeof(target))) {'
NEW_CALL = 'if (Port_FileAlias(rel, target, (unsigned)sizeof(target))) {'
OLD_DECL = '    extern int PortStages_Alias(const char *rel, char *out, unsigned n); /* plat_stages.c */'
NEW_DECL = '    extern int Port_FileAlias(const char *rel, char *out, unsigned size); /* plat_file.c */'


def transform_file(content: str) -> str:
    if 'int Port_FileAlias(const char *rel, char *out, unsigned size) {' in content:
        return content
    if content.count(MARKER) != 1:
        raise ValueError('plat_file.c: marqueur manquant ou ambigu')
    if 'static const char *alias_target(' not in content:
        raise ValueError('plat_file.c: resolver alias_target absent')
    return content.replace(MARKER, WRAPPER + MARKER)


def transform_fcache(content: str) -> str:
    if NEW_CALL in content and NEW_DECL in content:
        return content
    if content.count(OLD_CALL) != 1 or content.count(OLD_DECL) != 1:
        raise ValueError('plat_fcache.c: marqueur manquant, version du moteur differente')
    return content.replace(OLD_CALL, NEW_CALL).replace(OLD_DECL, NEW_DECL)


def process(root: Path, *, apply: bool, check: bool) -> int:
    files = {
        root / 'port/src/plat_file.c': transform_file,
        root / 'port/src/plat_fcache.c': transform_fcache,
    }
    for path, transform in files.items():
        source = path.read_text(encoding='utf-8')
        new = transform(source)
        if check and source != new:
            print(f'NON APPLIQUE : {path}')
            return 1
        if apply and source != new:
            path.write_text(new, encoding='utf-8', newline='')
        print(f'OK : {path.relative_to(root)}' + (' (aucun changement)' if source == new else ' (patchable)'))
    return 0


def main():
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--apply', action='store_true', help='Modifie deux fichiers C du code source du fork (pas le jeu)')
    g.add_argument('--check', action='store_true', help='Verifie que le patch est deja applique')
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    return process(args.repo, apply=args.apply, check=args.check)


if __name__ == '__main__':
    raise SystemExit(main())
