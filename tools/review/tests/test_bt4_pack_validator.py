"""Standard-library tests for the BT4 external character-package preflight."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "port" / "tools" / "bt4_pack_validator.py"
spec = importlib.util.spec_from_file_location("bt4_pack_validator", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class PackValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "characters"
        self.root.mkdir()

    def make_pack(self, folder="clone-mira", **manifest_changes):
        pack = self.root / folder
        pack.mkdir()
        for name in ("model.pak", "animations.pak", "effects.pak"):
            (pack / name).write_bytes(b"test asset")
        data = {
            "schema_version": 1,
            "name": "Mira - Test",
            "base_id": 236,
            "assets": {
                "model": "model.pak",
                "animations": "animations.pak",
                "effects": "effects.pak",
            },
        }
        data.update(manifest_changes)
        (pack / "character.json").write_text(json.dumps(data), encoding="utf-8")
        return pack

    def test_valid_pack_produces_hashes(self):
        self.make_pack()
        records, errors = mod.validate(self.root)
        self.assertFalse(errors)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["base_id"], 236)
        self.assertEqual(len(records[0]["assets"]["model"]["sha256"]), 64)

    def test_multiple_packs_are_sorted(self):
        self.make_pack("zeta")
        self.make_pack("alpha")
        records, errors = mod.validate(self.root)
        self.assertFalse(errors)
        self.assertEqual([p["folder"] for p in records], ["alpha", "zeta"])

    def test_rejects_parent_traversal(self):
        self.make_pack(assets={
            "model": "../elsewhere.pak",
            "animations": "animations.pak",
            "effects": "effects.pak",
        })
        records, errors = mod.validate(self.root)
        self.assertEqual(records, [])
        self.assertTrue(any("chemin" in e for e in errors))

    def test_rejects_windows_absolute(self):
        self.make_pack(assets={
            "model": "C:\\Users\\outside.pak",
            "animations": "animations.pak",
            "effects": "effects.pak",
        })
        _, errors = mod.validate(self.root)
        self.assertTrue(errors)

    def test_rejects_missing_required(self):
        self.make_pack(assets={"model": "model.pak"})
        _, errors = mod.validate(self.root)
        self.assertTrue(any("animations" in e for e in errors))

    def test_rejects_invalid_base(self):
        self.make_pack(base_id=250)
        _, errors = mod.validate(self.root)
        self.assertTrue(any("base_id" in e for e in errors))

    def test_refuses_empty_file(self):
        pack = self.make_pack()
        (pack / "effects.pak").write_bytes(b"")
        _, errors = mod.validate(self.root)
        self.assertTrue(any("vide" in e for e in errors))

    def test_cli_does_not_write_index_when_invalid(self):
        self.make_pack(base_id=250)
        index = self.root.parent / "index.json"
        self.assertEqual(mod.main(["--root", str(self.root), "--index", str(index)]), 1)
        self.assertFalse(index.exists())

    def test_cli_writes_index(self):
        self.make_pack()
        index = self.root.parent / "index.json"
        self.assertEqual(mod.main(["--root", str(self.root), "--index", str(index)]), 0)
        self.assertEqual(len(json.loads(index.read_text())["packs"]), 1)


if __name__ == "__main__":
    unittest.main()
