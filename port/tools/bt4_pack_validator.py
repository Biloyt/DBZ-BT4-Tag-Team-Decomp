#!/usr/bin/env python3
"""Validate external BT4 B14 Rev2 character packages without touching game files.

This is a package *preflight checker*. It does not implement character ID allocation,
resource aliasing, menu integration or an in-game loader.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = 1
MIN_BASE_ID = 0
MAX_BASE_ID = 249
REQUIRED_ASSETS = {"model", "animations", "effects"}
ASSET_EXTENSIONS = {
    "model": ".pak",
    "animations": ".pak",
    "effects": ".pak",
    "voice_jp": ".pak",
    "voice_us": ".pak",
    "portrait": ".bin",
    "member_p1": ".bin",
    "member_p2": ".bin",
}


def _safe_asset_path(folder: Path, value: object) -> Path | None:
    """Reject absolute, Windows, parent-traversal and out-of-package paths."""
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        return None
    if value.startswith("/") or any(part in ("", ".", "..") for part in value.split("/")):
        return None
    rel = PurePosixPath(value)
    if rel.is_absolute():
        return None
    resolved = (folder / str(rel)).resolve()
    try:
        resolved.relative_to(folder.resolve())
    except ValueError:
        return None
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(root: Path) -> tuple[list[dict], list[str]]:
    """Return reproducible package metadata and descriptive errors."""
    root = Path(root)
    errors: list[str] = []
    records: list[dict] = []
    if not root.is_dir():
        return [], [f"Dossier introuvable : {root}"]
    if root.is_symlink():
        return [], [f"Dossier racine symbolique interdit : {root}"]

    folders = sorted(root.iterdir(), key=lambda item: item.name.casefold())
    seen: set[str] = set()
    for folder in folders:
        if folder.name.startswith("."):
            continue
        if folder.is_symlink():
            errors.append(f"{folder.name}: dossier symbolique interdit")
            continue
        if not folder.is_dir():
            continue
        slug = folder.name.casefold()
        if slug in seen:
            errors.append(f"{folder.name}: doublon de dossier (casse differente)")
            continue
        seen.add(slug)
        manifest = folder / "character.json"
        if not manifest.is_file() or manifest.is_symlink():
            errors.append(f"{folder.name}: character.json absent ou lien symbolique")
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{folder.name}: character.json illisible ({exc})")
            continue
        if not isinstance(data, dict):
            errors.append(f"{folder.name}: manifeste doit etre un objet JSON")
            continue
        version = data.get("schema_version")
        if type(version) is not int or version != SCHEMA_VERSION:
            errors.append(f"{folder.name}: schema_version doit etre {SCHEMA_VERSION}")
            continue
        name = data.get("name")
        base = data.get("base_id")
        assets = data.get("assets")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 64:
            errors.append(f"{folder.name}: nom invalide (1 a 64 caracteres)")
            continue
        if type(base) is not int or not MIN_BASE_ID <= base <= MAX_BASE_ID:
            errors.append(f"{folder.name}: base_id doit etre entre 0 et 249")
            continue
        if not isinstance(assets, dict):
            errors.append(f"{folder.name}: assets doit etre un objet JSON")
            continue
        missing = REQUIRED_ASSETS - assets.keys()
        unknown = assets.keys() - ASSET_EXTENSIONS.keys()
        if missing:
            errors.append(f"{folder.name}: ressources manquantes : {', '.join(sorted(missing))}")
        if unknown:
            errors.append(f"{folder.name}: ressources inconnues : {', '.join(sorted(unknown))}")
        if missing or unknown:
            continue
        files: dict[str, dict] = {}
        ok = True
        for kind, asset in sorted(assets.items()):
            path = _safe_asset_path(folder, asset)
            if path is None or PurePosixPath(asset).suffix.lower() != ASSET_EXTENSIONS[kind]:
                errors.append(f"{folder.name}/{kind}: chemin ou extension invalide : {asset!r}")
                ok = False
                continue
            if not path.is_file():
                errors.append(f"{folder.name}/{kind}: fichier absent : {asset}")
                ok = False
                continue
            size = path.stat().st_size
            if size <= 0:
                errors.append(f"{folder.name}/{kind}: fichier vide : {asset}")
                ok = False
                continue
            files[kind] = {"path": asset, "bytes": size, "sha256": _sha256(path)}
        if ok:
            records.append({"folder": folder.name, "name": name.strip(), "base_id": base, "assets": files})
    return records, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preflight des packs de personnages BT4 (aucune modification du jeu)")
    parser.add_argument("--root", type=Path, default=Path("characters"), help="Dossier des packs externes")
    parser.add_argument("--index", type=Path, help="Fichier JSON d'index a generer si tout est valide")
    args = parser.parse_args(argv)
    packs, errors = validate(args.root)
    for err in errors:
        print("ERREUR:", err, file=sys.stderr)
    if errors:
        print(f"Echec : {len(errors)} erreur(s), aucun index ecrit.", file=sys.stderr)
        return 1
    output = {"schema_version": SCHEMA_VERSION, "compatibility": "bt4-b14-rev2", "packs": packs}
    if args.index is not None:
        args.index.parent.mkdir(parents=True, exist_ok=True)
        args.index.write_text(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Index ecrit : {args.index}")
    print(f"Verification OK : {len(packs)} pack(s) analyses. Aucun fichier du jeu modifie.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
