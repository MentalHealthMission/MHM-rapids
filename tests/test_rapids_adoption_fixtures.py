from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from connect_summary.rapids.adoption import connect_rapids_bridge, stage_connect_rapids_fixture
from mhm_core.rapids.adoption import RAPIDS_MODULE_ID, rapids_module_contract
from mhm_core.rapids.fixtures import stage_entity_metric_tree_for_rapids


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

    def test_connect_adapter_fixture_uses_same_neutral_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            merged = root / "merged"
            staging = root / "staging"
            self._write_gzip_csv(
                merged / "site-a" / "participant-1" / "phone_accelerometer" / "phone_accelerometer.csv.gz",
                "timestamp,x\n2026-05-18T08:00:00Z,0.1\n",
            )

            bridge = connect_rapids_bridge()
            result = stage_connect_rapids_fixture(
                merged_dir=merged,
                staging_dir=staging,
                inputs={"accelerometer": "phone_accelerometer"},
                entity_group_map={"participant-1": "site-a"},
            )

            self.assertEqual(bridge.validate(), [])
            self.assertEqual(result.containers, {"ACCELEROMETER": "phone_accelerometer.csv.gz"})
            self.assertTrue((result.staged_dir / "phone_accelerometer.csv.gz").exists())

    @staticmethod
    def _write_gzip_csv(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(text)


if __name__ == "__main__":
    unittest.main()
