from __future__ import annotations

import unittest

from mhm_core.rapids.features import RapidsFeatureKey, canonical_rapids_feature_id


class RapidsFeatureIdentityTests(unittest.TestCase):
    def test_identity_is_provider_and_group_qualified(self) -> None:
        identifier = canonical_rapids_feature_id(
            sensor="phone_steps",
            provider="rapids",
            group="daily",
            feature="sumsteps",
        )

        self.assertEqual(identifier, "rapids:PHONE_STEPS:RAPIDS:DAILY:sumsteps")
        self.assertEqual(RapidsFeatureKey.parse(identifier).identifier, identifier)

    def test_base_group_is_explicit(self) -> None:
        self.assertEqual(
            canonical_rapids_feature_id(
                sensor="PHONE_SCREEN",
                provider="RAPIDS",
                feature="total_unlocks",
            ),
            "rapids:PHONE_SCREEN:RAPIDS:BASE:total_unlocks",
        )

    def test_invalid_ambiguous_components_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not contain"):
            canonical_rapids_feature_id(
                sensor="PHONE:STEPS",
                provider="RAPIDS",
                feature="sumsteps",
            )


if __name__ == "__main__":
    unittest.main()
