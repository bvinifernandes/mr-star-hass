"""MR Star Garland leds count entity."""
from homeassistant import config_entries, core
from homeassistant.components.number import NumberEntity, RestoreNumber
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MrStarCoordinator


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Set up desk light."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([LEDCountEntity(
        data["coordinator"],
        data["info"],
        data["id"]
    )])

class LEDCountEntity(RestoreNumber, NumberEntity, CoordinatorEntity):
    """Garland LED count entity"""
    _value = 40
    _coordinator: MrStarCoordinator
    _attr_unique_id: str
    _attr_name: str
    _attr_native_step = 1
    _attr_native_min_value = 8
    _attr_native_max_value = 300
    _attr_icon = "mdi:counter"
    _available: bool

    def __init__(self, coordinator: MrStarCoordinator, info, entity_id: str):
        self._info = info
        self._id = entity_id
        self._attr_name = f"Garland {entity_id} LED count"
        self._attr_unique_id = self._attr_name
        self._coordinator = coordinator
        self._available = False
        super().__init__(coordinator)

    @property
    def device_info(self):
        return self._info

    @property
    def available(self) -> bool:
        return self._available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._available = self.coordinator.data["connected"]
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the entity value to represent the entity state."""
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        async with self._coordinator as light:
            if light is None:
                self._available = False
                return
            await light.set_length(int(value))
        self._value = value
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_number_data()
        if not state:
            return

        self._value = state.native_value
        if self._value > self._attr_native_max_value:
            self._value = self._attr_native_max_value
        elif self._value < self._attr_native_min_value:
            self._value = self._attr_native_min_value

        self._coordinator.create_on_connect_task(self.async_set_native_value(self._value))
