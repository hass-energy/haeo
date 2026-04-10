"""Connection segment types for composable connection architecture.

Each segment type applies a specific transformation or constraint to power flow:
- EfficiencySegment: Applies efficiency losses
- PassthroughSegment: Lossless passthrough (no constraints)
- PowerLimitSegment: Limits power flow with optional time-slice constraint
- PricingSegment: Adds transfer pricing costs
- SocPricingSegment: Adds SOC-based pricing penalties
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final, Literal, TypeGuard

from highspy import Highs
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.element import Element

from .efficiency import EfficiencySegment, EfficiencySegmentSpec
from .passthrough import PassthroughSegment, PassthroughSegmentSpec
from .power_limit import (
    POWER_LIMIT_SOURCE_TARGET,
    POWER_LIMIT_TARGET_SOURCE,
    POWER_LIMIT_TIME_SLICE,
    PowerLimitOutputName,
    PowerLimitSegment,
    PowerLimitSegmentSpec,
)
from .pricing import PricingSegment, PricingSegmentSpec
from .segment import Segment
from .soc_pricing import SocPricingSegment, SocPricingSegmentSpec
from .tag_filter import TagFilterSegment, TagFilterSegmentSpec
from .tag_pricing import TagPricingSegment, TagPricingSegmentSpec

# Discriminated union of segment type strings
type SegmentType = Literal["efficiency", "passthrough", "power_limit", "pricing", "soc_pricing", "tag_pricing", "tag_filter"]

# Union type for all segment specifications
type SegmentSpec = (
    EfficiencySegmentSpec
    | PassthroughSegmentSpec
    | PowerLimitSegmentSpec
    | PricingSegmentSpec
    | SocPricingSegmentSpec
    | TagPricingSegmentSpec
    | TagFilterSegmentSpec
)


def is_efficiency_spec(spec: SegmentSpec) -> TypeGuard[EfficiencySegmentSpec]:
    """Return True when spec is for an efficiency segment."""
    return spec["segment_type"] == "efficiency"


def is_passthrough_spec(spec: SegmentSpec) -> TypeGuard[PassthroughSegmentSpec]:
    """Return True when spec is for a passthrough segment."""
    return spec["segment_type"] == "passthrough"


def is_power_limit_spec(spec: SegmentSpec) -> TypeGuard[PowerLimitSegmentSpec]:
    """Return True when spec is for a power limit segment."""
    return spec["segment_type"] == "power_limit"


def is_pricing_spec(spec: SegmentSpec) -> TypeGuard[PricingSegmentSpec]:
    """Return True when spec is for a pricing segment."""
    return spec["segment_type"] == "pricing"


def is_soc_pricing_spec(spec: SegmentSpec) -> TypeGuard[SocPricingSegmentSpec]:
    """Return True when spec is for a SOC pricing segment."""
    return spec["segment_type"] == "soc_pricing"


def is_tag_pricing_spec(spec: SegmentSpec) -> TypeGuard[TagPricingSegmentSpec]:
    """Return True when spec is for a tag pricing segment."""
    return spec["segment_type"] == "tag_pricing"


def is_tag_filter_spec(spec: SegmentSpec) -> TypeGuard[TagFilterSegmentSpec]:
    """Return True when spec is for a tag filter segment."""
    return spec["segment_type"] == "tag_filter"


@dataclass(frozen=True, slots=True)
class SegmentSpecEntry:
    """Specification for a segment type."""

    factory: Callable[..., Segment]


# Registry mapping segment type strings to segment factories
SEGMENTS: Final[dict[SegmentType, SegmentSpecEntry]] = {
    "efficiency": SegmentSpecEntry(factory=EfficiencySegment),
    "passthrough": SegmentSpecEntry(factory=PassthroughSegment),
    "power_limit": SegmentSpecEntry(factory=PowerLimitSegment),
    "pricing": SegmentSpecEntry(factory=PricingSegment),
    "soc_pricing": SegmentSpecEntry(factory=SocPricingSegment),
    "tag_pricing": SegmentSpecEntry(factory=TagPricingSegment),
    "tag_filter": SegmentSpecEntry(factory=TagFilterSegment),
}


def create_segment(
    *,
    segment_id: str,
    n_periods: int,
    periods: NDArray[np.floating[Any]],
    solver: Highs,
    spec: SegmentSpec,
    source_element: Element[Any],
    target_element: Element[Any],
    tags: list[str] | None = None,
) -> Segment:
    """Create a segment instance from a segment specification."""
    segment_type = spec["segment_type"]
    entry = SEGMENTS[segment_type]
    segment = entry.factory(
        segment_id,
        n_periods,
        periods,
        solver,
        spec=spec,
        source_element=source_element,
        target_element=target_element,
    )
    # Set tags on the segment (must be done after construction
    # because subclass constructors create the total power variables first)
    if tags:
        segment._tags = list(tags)  # noqa: SLF001
    return segment


__all__ = [
    "POWER_LIMIT_SOURCE_TARGET",
    "POWER_LIMIT_TARGET_SOURCE",
    "POWER_LIMIT_TIME_SLICE",
    "SEGMENTS",
    "EfficiencySegment",
    "EfficiencySegmentSpec",
    "PassthroughSegment",
    "PassthroughSegmentSpec",
    "PowerLimitOutputName",
    "PowerLimitSegment",
    "PowerLimitSegmentSpec",
    "PricingSegment",
    "PricingSegmentSpec",
    "Segment",
    "SegmentSpec",
    "SegmentSpecEntry",
    "SegmentType",
    "SocPricingSegment",
    "SocPricingSegmentSpec",
    "create_segment",
    "is_efficiency_spec",
    "is_passthrough_spec",
    "is_power_limit_spec",
    "is_pricing_spec",
    "is_soc_pricing_spec",
    "is_tag_filter_spec",
    "is_tag_pricing_spec",
    "TagFilterSegment",
    "TagFilterSegmentSpec",
    "TagPricingSegment",
    "TagPricingSegmentSpec",
]
