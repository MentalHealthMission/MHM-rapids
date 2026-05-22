from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from mhm_core.rapids.adoption import RAPIDS_MODULE_ID, rapids_module_contract
from mhm_core.rapids.fixtures import stage_entity_metric_tree_for_rapids
from mhm_core.rapids.staging import stage_rapids_metric_inputs


class RapidsAdoptionFixtureTests(unittest.TestCase):
    def test_neutral_rapids_contract_lives_in_mhm_module(self) -> None:
        contract = rapids_module_contract()

        self.assertEqual(contract.module_id, RAPIDS_MODULE_ID)
        self.assertIn("entity_metric_tree", contract.required_inputs)
        self.assertIn("entity_group_map", contract.required_inputs)
        self.assertIn("rapids_manifest", contract.produced_outputs)

    def test_neutral_fixture_stages_entity_metric_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metric_tree = root / "metric-tree"
            staging = root / "staging"
            self._write_gzip_csv(
                metric_tree / "group-a" / "entity-alpha" / "phone_steps" / "phone_steps.csv.gz",
                "timestamp,value\n2026-05-18T08:00:00Z,10\n",
            )
            self._write_gzip_csv(
                metric_tree / "group-a" / "entity-beta" / "phone_steps" / "phone_steps.csv.gz",
                "timestamp,value\n2026-05-18T08:05:00Z,20\n",
            )

            result = stage_entity_metric_tree_for_rapids(
                metric_tree_root=metric_tree,
                staging_dir=staging,
                inputs={"steps": {"android": "phone_steps"}},
                entity_group_map={"entity-alpha": "group-a", "entity-beta": "group-a"},
            )

            staged_file = result.staged_dir / "phone_steps.csv.gz"
            self.assertTrue(staged_file.exists())
            with gzip.open(staged_file, "rt", encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            self.assertEqual(
                lines,
                [
                    "timestamp,value",
                    "2026-05-18T08:00:00Z,10",
                    "2026-05-18T08:05:00Z,20",
                ],
            )
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["module_id"], "mhm.rapids")
            self.assertEqual(manifest["containers"], {"STEPS": "phone_steps.csv.gz"})

    def test_neutral_staging_can_keep_platform_containers_separate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metric_tree = root / "metric-tree"
            staging = root / "staging"
            self._write_gzip_csv(
                metric_tree / "group-a" / "entity-alpha" / "android_steps" / "android_steps.csv.gz",
                "timestamp,value\n2026-05-18T08:00:00Z,10\n",
            )
            self._write_gzip_csv(
                metric_tree / "group-a" / "entity-alpha" / "ios_steps" / "ios_steps.csv.gz",
                "timestamp,value\n2026-05-18T08:05:00Z,20\n",
            )

            result = stage_rapids_metric_inputs(
                metric_tree_root=metric_tree,
                staged_root=staging,
                inputs={"steps": {"android": "android_steps", "ios": "ios_steps"}},
                entity_group_map={"entity-alpha": "group-a"},
                entities=["entity-alpha"],
                combine_multi_platform=False,
            )

            self.assertEqual(
                result.containers,
                {"STEPS": {"ANDROID": "android_steps.csv.gz", "IOS": "ios_steps.csv.gz"}},
            )

    @staticmethod
    def _write_gzip_csv(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(text)


if __name__ == "__main__":
    unittest.main()
