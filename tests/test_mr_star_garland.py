"""Tests for the MR Star Garland integration.

These cover the parts that are pure logic plus the coordinator shutdown
path, which previously blocked forever when the garland was unreachable.
"""

import asyncio
import logging
import time
from types import SimpleNamespace

import pytest
from mr_star_ble import Effect

from custom_components.mr_star_garland import short_id
from custom_components.mr_star_garland import coordinator as coordinator_module
from custom_components.mr_star_garland.coordinator import MrStarCoordinator
from custom_components.mr_star_garland.light import (
    EFFECT_LIST,
    EFFECTS,
    LEGACY_EFFECT_NAMES,
    MrStarLightEntity,
)
from custom_components.mr_star_garland.number import LEDCountEntity

ADDRESS = "AA:BB:CC:DD:EE:FF"


def test_every_effect_is_exposed():
    """The effect list must cover the whole firmware effect enum."""
    assert set(EFFECTS.values()) == set(Effect)


def test_effect_names_are_unique():
    """Two effects must not collapse onto the same display name."""
    assert len(EFFECT_LIST) == len(set(EFFECT_LIST)) == len(list(Effect))


def test_legacy_effect_names_still_resolve():
    """Automations selecting the original names must keep working."""
    for name, effect in LEGACY_EFFECT_NAMES.items():
        assert EFFECTS[name] is effect


def test_acronyms_are_not_title_cased():
    """Colour-code abbreviations stay upper case."""
    assert "RGB Fluttering" in EFFECT_LIST
    assert "Rgb Fluttering" not in EFFECT_LIST


def test_short_id_matches_the_original_algorithm():
    """Device and entity names must not change for existing installs."""
    assert short_id(ADDRESS) == ADDRESS[len(ADDRESS) - 5 :].replace(":", "")
    assert short_id(ADDRESS) == "EEFF"


def _fake_entry(coordinator):
    """Build the minimum config entry shape the entities read."""
    return SimpleNamespace(
        runtime_data=SimpleNamespace(
            coordinator=coordinator,
            device_info={"identifiers": {("mr_star_garland", ADDRESS)}},
            address=ADDRESS,
        )
    )


def _bare_coordinator():
    """Build a coordinator without going through DataUpdateCoordinator."""
    coordinator = MrStarCoordinator.__new__(MrStarCoordinator)
    coordinator.hass = SimpleNamespace(
        async_create_background_task=lambda coro, name=None: asyncio.ensure_future(coro)
    )
    coordinator.logger = logging.getLogger("test")
    coordinator.async_set_updated_data = lambda data: setattr(coordinator, "data", data)
    coordinator._address = ADDRESS
    coordinator._ttl = 120
    coordinator._connection_timeout = 30
    coordinator._client = None
    coordinator._lock = asyncio.Lock()
    coordinator._stopping = asyncio.Event()
    coordinator._connected = asyncio.Event()
    coordinator._session_task = None
    coordinator._pending_tasks = set()
    coordinator.data = {"connected": False}
    return coordinator


def test_entities_use_address_based_unique_ids():
    """Unique IDs must be derived from the full address, not a display name."""
    coordinator = _bare_coordinator()
    entry = _fake_entry(coordinator)

    lamp = MrStarLightEntity(entry)
    counter = LEDCountEntity(entry)

    assert lamp.unique_id == f"{ADDRESS}_light"
    assert counter.unique_id == f"{ADDRESS}_led_count"
    assert lamp.unique_id != counter.unique_id


def test_availability_follows_the_session_not_the_power_state():
    """An off garland on a live session is available, not unavailable."""
    coordinator = _bare_coordinator()
    lamp = MrStarLightEntity(_fake_entry(coordinator))

    coordinator.data = {"connected": False}
    assert lamp.available is False

    coordinator.data = {"connected": True}
    assert lamp.available is True
    assert lamp.is_on is False


@pytest.mark.asyncio
async def test_stop_returns_while_the_garland_is_unreachable(monkeypatch):
    """Unloading must not block on a device that cannot be connected to.

    The session task spends most of its time in the reconnect backoff when
    the garland is out of range. Stopping has to interrupt that wait.
    """
    monkeypatch.setattr(
        coordinator_module.bluetooth,
        "async_ble_device_from_address",
        lambda hass, address, connectable=True: None,
    )

    coordinator = _bare_coordinator()
    await coordinator.start()
    await asyncio.sleep(0.2)

    started = time.monotonic()
    await coordinator.stop()
    elapsed = time.monotonic() - started

    assert elapsed < 1.0, f"stop() took {elapsed:.1f}s"
    assert coordinator.data == {"connected": False}
