import struct
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
