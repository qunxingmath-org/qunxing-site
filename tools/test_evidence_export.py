"""Check the public evidence sidecar without changing problem-card or page outputs."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from build_problems import api, build, load


class EvidenceExportTests(unittest.TestCase):
    def test_public_sidecars_preserve_cards_and_exclude_private_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            problems = data / "problems/000"
            problems.mkdir(parents=True)
            for number, visibility in ((1, "public"), (2, "private")):
                pid = f"QX-P-{number:06d}"
                meta = {"schema": "qunxing.problem/2", "id": pid, "card_rev": "a" * 16,
                        "visibility": visibility, "title": "Fixture", "track": "open"}
                (problems / f"{pid}.meta.json").write_bytes((json.dumps(meta, indent=2) + "\n").encode())
                (problems / f"{pid}.text.md").write_bytes(b"## Statement\n\nFixture.\n")
            cards = load(data)
            original = api(cards, "b" * 40)
            self.assertEqual(api(cards, "b" * 40, data), original)

            evidence_dir = data / "evidence/000"
            evidence_dir.mkdir(parents=True)
            evidence = {"schema": "qunxing.evidence/1", "id": "QX-P-000001", "card_rev": "a" * 16,
                        "summary": {"search_coverage": {"value": "item_basic_gaps", "routes": ["detail-only"]},
                                    "claim": {"state": "proved_claimed", "review": "pending", "url": "detail-only"},
                                    "legacy": True}}
            raw = (json.dumps(evidence, indent=2) + "\n").encode()
            (evidence_dir / "QX-P-000001.json").write_bytes(raw)
            (evidence_dir / "QX-P-000002.json").write_bytes(b"private-card-marker")
            (data / "novelty/inbox").mkdir(parents=True)
            (data / "novelty/inbox/private.jsonl").write_bytes(b"private-inbox-marker")
            (data / "schema").mkdir()
            vocab = b'{"schema":"qunxing.vocab/1"}\n'
            (data / "schema/qunxing.vocab-1.json").write_bytes(vocab)

            result = api(cards, "b" * 40, data)
            for path, value in original.items():
                if path != "api/v1/index.json":
                    self.assertEqual(result[path], value)
            self.assertEqual(result["api/v1/evidence/QX-P-000001.json"], raw)
            self.assertEqual(result["api/v1/vocab.json"], vocab)
            index = json.loads(result["api/v1/evidence.json"])
            self.assertEqual(index["source"]["commit"], "b" * 40)
            self.assertEqual(index["count"], 1)
            self.assertEqual(index["items"][0]["summary"], {"search_coverage": "item_basic_gaps",
                             "claim": {"state": "proved_claimed", "review": "pending"}})
            self.assertNotIn(b"detail-only", result["api/v1/evidence.json"])
            discovery = json.loads(result["api/v1/index.json"])
            previous = json.loads(original["api/v1/index.json"])
            for key, value in previous["files"].items():
                self.assertEqual(discovery["files"][key], value)
            self.assertEqual(set(discovery["files"]) - set(previous["files"]),
                             {"evidence", "problem_evidence", "vocabulary"})
            self.assertNotIn("api/v1/evidence/QX-P-000002.json", result)
            self.assertNotIn(b"private-card-marker", b"".join(result.values()))
            self.assertNotIn(b"private-inbox-marker", b"".join(result.values()))

            # Different data snapshots change only JSON; page sources keep their original commit.
            with patch("build_problems.data_commit", side_effect=lambda path: "c" * 40 if path == data else "b" * 40), \
                    patch("build_problems.load", return_value=cards):
                baseline, old_bank = build(data / "page-snapshot")
                split, split_bank = build(data / "page-snapshot", data)
            self.assertEqual(old_bank, split_bank)
            self.assertEqual({p: v for p, v in baseline.items() if not p.startswith("api/v1/")},
                             {p: v for p, v in split.items() if not p.startswith("api/v1/")})
            self.assertEqual(json.loads(split["api/v1/index.json"])["source"]["commit"], "c" * 40)
            self.assertEqual(json.loads(split_bank)["source"]["commit"], "b" * 40)


if __name__ == "__main__":
    unittest.main()
