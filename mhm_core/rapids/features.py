"""Stable identities for RAPIDS feature definitions."""
from __future__ import annotations

from dataclasses import dataclass


RAPIDS_FEATURE_ID_PREFIX = "rapids"


def _identity_part(value: object, *, field: str, upper: bool = False) -> str:
    part = str(value or "").strip()
    if not part:
        raise ValueError(f"RAPIDS feature {field} must not be empty")
    if ":" in part:
        raise ValueError(f"RAPIDS feature {field} must not contain ':'")
    return part.upper() if upper else part


@dataclass(frozen=True, order=True)
class RapidsFeatureKey:
    """Provider-qualified RAPIDS feature identity."""

    sensor: str
    provider: str
    group: str
    feature: str

    @classmethod
    def create(
        cls,
        *,
        sensor: object,
        provider: object,
        feature: object,
        group: object | None = None,
    ) -> "RapidsFeatureKey":
        return cls(
            sensor=_identity_part(sensor, field="sensor", upper=True),
            provider=_identity_part(provider, field="provider", upper=True),
            group=_identity_part(group or "BASE", field="group", upper=True),
            feature=_identity_part(feature, field="name"),
        )

    @classmethod
    def parse(cls, value: str) -> "RapidsFeatureKey":
        parts = str(value).split(":")
        if len(parts) != 5 or parts[0] != RAPIDS_FEATURE_ID_PREFIX:
            raise ValueError(
                "RAPIDS feature id must use "
                "'rapids:<sensor>:<provider>:<group>:<feature>'"
            )
        return cls.create(
            sensor=parts[1],
            provider=parts[2],
            group=parts[3],
            feature=parts[4],
        )

    @property
    def identifier(self) -> str:
        return ":".join(
            (
                RAPIDS_FEATURE_ID_PREFIX,
                self.sensor,
                self.provider,
                self.group,
                self.feature,
            )
        )


def canonical_rapids_feature_id(
    *,
    sensor: object,
    provider: object,
    feature: object,
    group: object | None = None,
) -> str:
    """Return the canonical, provider-qualified RAPIDS feature id."""

    return RapidsFeatureKey.create(
        sensor=sensor,
        provider=provider,
        group=group,
        feature=feature,
    ).identifier
