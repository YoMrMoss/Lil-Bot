import struct
import unittest
from pathlib import Path
import re

import companion


ROOT = Path(__file__).resolve().parent


class FirmwareAssetTests(unittest.TestCase):
    def test_generated_faces_match_display(self):
        files = sorted((ROOT / "firmware" / "data" / "faces").glob("*.lbf"))
        self.assertGreaterEqual(len(files), 7)
        for path in files:
            blob = path.read_bytes()
            self.assertEqual(blob[:4], b"LBF1")
            version, width, height, frames, delay = struct.unpack("<BHHBH", blob[4:12])
            self.assertEqual((version, width, height, frames), (1, 320, 170, 1))
            self.assertGreater(delay, 0)
            self.assertEqual(len(blob), 12 + ((width * height + 7) // 8) * frames)

    def test_animation_lab_and_firmware_share_canonical_palette(self):
        preview = (ROOT / "display-preview.html").read_text(encoding="utf-8")
        firmware = (ROOT / "firmware" / "src" / "main.cpp").read_text(encoding="utf-8")
        self.assertIn("const C='#19f7ff',P='#ff2daa',V='#8b3dff'", preview)
        self.assertIn("gfx->color565(25, 247, 255)", firmware)
        self.assertIn("gfx->color565(255, 45, 170)", firmware)
        self.assertIn("gfx->color565(139, 61, 255)", firmware)

    def test_animation_lab_covers_all_renderable_companion_states(self):
        preview = (ROOT / "display-preview.html").read_text(encoding="utf-8")
        expression_block = re.search(r"const expressions=\{(.+?)\};", preview).group(1)
        preview_states = set(re.findall(r"(?:^|,)([a-z_]+):\[", expression_block))
        self.assertEqual(preview_states, companion.VALID_STATES - {"time", "weather"})

    def test_new_glyphs_and_orc_exist_in_both_renderers(self):
        preview = (ROOT / "display-preview.html").read_text(encoding="utf-8")
        firmware = (ROOT / "firmware" / "src" / "main.cpp").read_text(encoding="utf-8")
        for state in ("launch_chrome", "launch_spotify", "launch_discord", "orc"):
            self.assertIn(state, preview)
            self.assertIn(state, firmware)


if __name__ == "__main__":
    unittest.main()
