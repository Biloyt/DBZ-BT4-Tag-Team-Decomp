import importlib.util
import pathlib
import tempfile
import unittest

script = pathlib.Path(__file__).resolve().parents[3] / 'port/tools/bt4_patch_alias_runtime.py'
spec = importlib.util.spec_from_file_location('bt4_patch_alias_runtime', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

FILE = '''#include <stdio.h>
static const char *alias_target(const char *rel) { return rel; }
static PortFile *open_rel(const char *rel) { return 0; }
'''
FCACHE = '''FILE *Port_FileOpenHost(const char *rel, char *path, size_t n) {
    extern int PortStages_Alias(const char *rel, char *out, unsigned n); /* plat_stages.c */
    extern int PortSongs_Alias(const char *rel, char *out, unsigned n);
    char target[256];
    if (PortStages_Alias(rel, target, (unsigned)sizeof(target)) || PortSongs_Alias(rel, target, (unsigned)sizeof(target))) {
        return 0;
    }
    return 0;
}
'''

class AliasSourcePatchTest(unittest.TestCase):
    def test_file_wrapper_added_once(self):
        updated = module.transform_file(FILE)
        self.assertIn('int Port_FileAlias(', updated)
        self.assertEqual(module.transform_file(updated), updated)

    def test_cache_uses_shared_resolver(self):
        updated = module.transform_fcache(FCACHE)
        self.assertIn('if (Port_FileAlias(', updated)
        self.assertEqual(module.transform_fcache(updated), updated)

    def test_fail_closed_on_unknown_version(self):
        with self.assertRaises(ValueError):
            module.transform_file('no markers')
        with self.assertRaises(ValueError):
            module.transform_fcache('no markers')

    def test_source_patch_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            path = root / 'port/src'; path.mkdir(parents=True)
            (path / 'plat_file.c').write_text(FILE)
            (path / 'plat_fcache.c').write_text(FCACHE)
            self.assertEqual(module.process(root, apply=True, check=False), 0)
            self.assertEqual(module.process(root, apply=False, check=True), 0)

if __name__ == '__main__':
    unittest.main()
