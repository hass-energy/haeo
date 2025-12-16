---
applyTo: "tests/**"
---

# Testing standards

## Coverage requirements

- Target >95% test coverage for all modules
- 100% coverage for config flows

## Best practices

- Use pytest fixtures from `tests.common`
- Mock all external dependencies
- Use snapshot testing for complex data structures
- Never access `hass.data` directly - use fixtures and proper integration setup
- Test through integration setup, not entities in isolation
- Verify entities are properly registered with devices

## Property access in tests

When you have created entities in a test, access their properties directly without None checks:

```python
# ✅ Good - direct access
battery = network.elements["battery"]
assert battery.power == 1000

# ❌ Bad - unnecessary None checks
battery = network.elements.get("battery")
if battery is not None:
    assert battery.power == 1000
```

None checks reduce readability and make tests fragile to passing unexpectedly.

## Fixture patterns

```python
@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return mocked config entry."""
    return MockConfigEntry(
        title="Test Network",
        domain=DOMAIN,
        data={...},
        unique_id="test_unique_id",
    )

@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> MockConfigEntry:
    """Set up integration for testing."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
```

## Config flow testing

Test all paths:

```python
async def test_user_flow_success(hass):
    """Test successful user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={...}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

async def test_flow_connection_error(hass, mock_api_error):
    """Test connection error handling."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={...}
    )
    assert result["errors"] == {"base": "cannot_connect"}
```

## Snapshot testing

Use snapshots for entity states:

```python
@pytest.mark.usefixtures("init_integration")
async def test_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensor entities."""
    await snapshot_platform(
        hass, entity_registry, snapshot, mock_config_entry.entry_id
    )
```

## Mock patterns

```python
@pytest.fixture
def mock_api() -> Generator[MagicMock]:
    """Mock the API client."""
    with patch("custom_components.haeo.MyClient") as mock:
        client = mock.return_value
        client.get_data.return_value = {"value": 100}
        yield client
```
