"""Regression tests for release activation, mirror integrity and update metadata."""
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from xml.etree import ElementTree

from build_manifest import manifest
from build_site import full_text, sitemap
from release_assets import ASSETS, latest, mirror_present, sync_mirror


def sample():
    contents = {name: f"fixture-{role}".encode() for role, name in ASSETS.items()}
    metadata = {"tag_name": "v0.9.0", "published_at": "2026-11-25T09:00:00Z",
                "draft": False, "prerelease": False,
                "assets": [{"name": name, "size": len(data), "digest": "sha256:" + sha256(data).hexdigest()}
                           for name, data in contents.items()]}
    sums = "".join(f"{sha256(data).hexdigest()}  {name}\n" for name, data in contents.items())
    return metadata, contents, sums.encode()


class ReleaseTests(unittest.TestCase):
    def test_no_release_stays_unavailable(self):
        error = HTTPError("https://example.org", 404, "missing", None, None)
        with patch("release_assets.fetch", side_effect=error):
            self.assertIsNone(latest())

    def test_verified_assets_publish_together_and_repeat(self):
        metadata, contents, sums = sample()
        with patch("release_assets.fetch", side_effect=[BytesIO(json.dumps(metadata).encode()), BytesIO(sums)]):
            release = latest()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/"downloads"
            with patch("release_assets.fetch", side_effect=[BytesIO(contents[name]) for name in ASSETS.values()]):
                target = sync_mirror(release, output)
            self.assertEqual((target/"SHA256SUMS.txt").read_bytes(), sums)
            self.assertEqual(sync_mirror(release, output), target)
            with patch("release_assets.fetch", return_value=BytesIO(sums)):
                self.assertTrue(mirror_present(release))

    def test_wrong_digest_does_not_publish(self):
        metadata, _, sums = sample()
        with patch("release_assets.fetch", side_effect=[BytesIO(json.dumps(metadata).encode()), BytesIO(sums)]):
            release = latest()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/"downloads"
            with patch("release_assets.fetch", return_value=BytesIO(b"wrong")), self.assertRaises(ValueError):
                sync_mirror(release, output)
            self.assertFalse((output/"v0.9.0").exists())

    def test_key_expiry_and_package_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = Path(tmp)
            (assets/"prices.json").write_bytes(b"{}")
            keys = {"epoch": 2, "keys": [{"id": "fixture", "public_key": "test-public",
                                        "expires_at": "2026-12-02T00:00:00Z"}]}
            policy = {"epoch": 2, "version": 4, "key_id": "fixture", "min_app_version": "0.9.0",
                      "mirrors": ["https://www.qunxingmath.org/"], "inbox_endpoints": [],
                      "packages": {"prices": "prices.json"}}
            values, _ = manifest(policy, keys, assets, datetime(2026, 11, 25, tzinfo=timezone.utc))
            self.assertEqual(values["expires_at"], "2026-12-02T00:00:00Z")
            self.assertEqual(values["packages"]["prices"]["sha256"], sha256(b"{}").hexdigest())

    def test_text_extract_and_sitemap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/"problems").mkdir()
            (root/"problems/index.html").write_text("<nav>menu</nav><main>数学题库</main>", encoding="utf-8")
            (root/"llms.txt").write_text("[题库](https://www.qunxingmath.org/problems/)", encoding="utf-8")
            sitemap(root)
            full_text(root)
            self.assertIn("数学题库", (root/"llms-full.txt").read_text(encoding="utf-8"))
            self.assertNotIn("menu", (root/"llms-full.txt").read_text(encoding="utf-8"))
            self.assertEqual(len(ElementTree.parse(root/"sitemap.xml").getroot()), 1)


if __name__ == "__main__":
    unittest.main()
