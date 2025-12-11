"""Additional validation coverage for Network endpoints."""

import pytest

from custom_components.haeo.model import Network
from custom_components.haeo.model.connection import Connection
from custom_components.haeo.model.source_sink import SourceSink


def test_validate_raises_when_source_missing() -> None:
    """Validate should raise when a connection source is missing."""

    net = Network(name="net", period=1.0, n_periods=1)
    net.elements["conn"] = Connection(
        name="conn",
        period=1.0,
        n_periods=1,
        source="missing",
        target="also_missing",
    )

    with pytest.raises(ValueError, match="Source element 'missing' not found"):
        net.validate()


def test_validate_raises_when_endpoints_are_connections() -> None:
    """Validate should reject connections that point to connection elements."""

    net = Network(name="net", period=1.0, n_periods=1)
    # Non-connection element to satisfy target for conn2
    net.elements["node"] = SourceSink(name="node", period=1.0, n_periods=1, is_source=True, is_sink=True)

    net.elements["conn2"] = Connection(
        name="conn2",
        period=1.0,
        n_periods=1,
        source="node",
        target="node",
    )

    # conn1 references conn2 as source and target to hit both connection checks
    net.elements["conn1"] = Connection(
        name="conn1",
        period=1.0,
        n_periods=1,
        source="conn2",
        target="conn2",
    )

    with pytest.raises(ValueError, match="Source element 'conn2' is a connection"):
        net.validate()


def test_validate_raises_when_target_missing() -> None:
    """Validate should raise when a connection target is missing."""

    net = Network(name="net", period=1.0, n_periods=1)
    net.elements["source_node"] = SourceSink(name="source_node", period=1.0, n_periods=1, is_source=True, is_sink=True)
    net.elements["conn"] = Connection(
        name="conn",
        period=1.0,
        n_periods=1,
        source="source_node",
        target="missing_target",
    )

    with pytest.raises(ValueError, match="Target element 'missing_target' not found"):
        net.validate()


def test_constraints_returns_empty_when_no_elements() -> None:
    """Constraints should return empty list when network has no elements."""

    net = Network(name="net", period=1.0, n_periods=1)

    assert net.constraints() == []
