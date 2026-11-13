import importlib.util
from pathlib import Path
import unittest
import tempfile

SCRIPT = Path(__file__).resolve().parents[3] / 'port/tools/bt4_patch_id250_runtime.py'
spec = importlib.util.spec_from_file_location('bt4_id250_patch', SCRIPT)
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)

class TestID250Patch(unittest.TestCase):
    def test_header_preserves_non_port_250(self):
        s = 'x\n#define CHRVIEW_CHARA_COUNT 250\ny'
        r = patch.header(s)
        self.assertIn('#ifdef PORT\n#define CHRVIEW_CHARA_COUNT 251', r)
        self.assertIn('#else\n#define CHRVIEW_CHARA_COUNT 250\n#endif', r)
        self.assertEqual(r, patch.header(r))

    def test_model_id_reverse_loop(self):
        s = 'for (c = 0; c < 250; c++) {\n    return c;\n}'
        r = patch.viewer(s)
        self.assertIn('c < CHRVIEW_CHARA_COUNT', r)
        self.assertEqual(r, patch.viewer(r))

    def test_four_cursor_checks_and_unlock_macro(self):
        s = '\n'.join(['(id >= 0xA5 && id < 250)'] * 4) + \
            '\n#define CHARA_UNLOCKED(id) (((id) >= 0xA5 && (id) < 250) || other)'
        r = patch.grid(s)
        self.assertEqual(r.count(patch.NEW_GRID), 4)
        self.assertIn(patch.NEW_UNLOCK, r)
        self.assertEqual(r, patch.grid(r))

    def test_ambiguous_source_is_rejected(self):
        with self.assertRaises(ValueError):
            patch.grid('(id >= 0xA5 && id < 250)')
        with self.assertRaises(ValueError):
            patch.header('#define CHRVIEW_CHARA_COUNT 249')

    def test_process_check_then_apply(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for p, data in {
                'include/battle/view_a.h': '#define CHRVIEW_CHARA_COUNT 250',
                'src/battle/view_a_d.c': 'for (c = 0; c < 250; c++) {}',
                'src/battle/view_a_e.c': ('(id >= 0xA5 && id < 250)\n'*4 +
                    '#define CHARA_UNLOCKED(id) (((id) >= 0xA5 && (id) < 250) || other)'),
            }.items():
                q=root/p; q.parent.mkdir(parents=True,exist_ok=True); q.write_text(data)
            self.assertEqual(patch.process(root, apply=False), 1)
            self.assertEqual(patch.process(root, apply=True), 0)
            self.assertEqual(patch.process(root, apply=False), 0)

if __name__ == '__main__': unittest.main()
