"""MyrtDesk light integration"""
from types import CoroutineType
from typing import Any

import homeassistant.util.color as color_util
from homeassistant import config_entries, core
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    COLOR_MODE_HS,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import callback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from mr_star_ble import Effect

from .const import DOMAIN
from .coordinator import MrStarCoordinator

EFFECTS_MAPPING = {
    "Automatic Loop": Effect.AUTOMATIC_LOOP,
    "Symphony": Effect.SYMPHONY,
    "Fluttering": Effect.COLORFUL_FLUTTERING,
    "Open & Close": Effect.RAINBOW_OPEN_CLOSE,
    "Light & Dark Transition": Effect.RAINBOW_LIGHT_DARK_TRANSITION,
    "Flowing Water": Effect.RAINBOW_FLOWING_WATER
}

EFFECT_LIST = list(EFFECTS_MAPPING.keys())
EFFECT_LIST.sort()

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Set up desk light."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([MrStarLightEntity(
        data["coordinator"],
        data["info"],
        data["id"]
    )])

class MrStarLightEntity(LightEntity, CoordinatorEntity, RestoreEntity):
    """MyrtDesk backlight entity"""
    _is_on: bool = False
    _rgb: tuple[int, int, int] = (255, 255, 255)
    _brightness: int = 255
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_supported_color_modes = {ColorMode.XY, ColorMode.BRIGHTNESS}
    _attr_effect_list = EFFECT_LIST
    _attr_effect = EFFECT_LIST[0]
    _attr_name: str
    _attr_unique_id: str
    _available: bool
    _coordinator: MrStarCoordinator

    def __init__(self, coordinator: MrStarCoordinator, info, entity_id: str):
        self._info = info
        self._id = entity_id
        self._coordinator = coordinator
        self._attr_name = f"Garland {entity_id} Light"
        self._attr_unique_id = self._attr_name
        self._available = False
        super().__init__(coordinator)

    @property
    def device_info(self):
        return self._info

    @property
    def available(self) -> bool:
        return self._available

    @property
    def icon(self):
        return "mdi:led-strip-variant"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._available = self.coordinator.data["connected"]
        self.async_write_ha_state()

    @property
    def brightness(self) -> int:
        """Return the brightness of the device."""
        return self._brightness

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._is_on

    @property
    def color_mode(self) -> ColorMode:
        return ColorMode.HS

    @property
    def supported_color_modes(self) -> set:
        """Flag supported color modes."""
        return {COLOR_MODE_HS}

    @property
    def hs_color(self) -> tuple[int, int, int]:
        """Return the color of the device."""
        return color_util.color_RGB_to_hs(*self._rgb)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Update the current value."""
        async with self._coordinator as light:
            if light is None:
                self._available = False
                return
            if not self._is_on:
                await light.set_power(True)
                self._is_on = True
            if ATTR_BRIGHTNESS in kwargs:
                self._brightness = kwargs[ATTR_BRIGHTNESS]
                await light.set_brightness(float(self._brightness) / float(255))
            if ATTR_HS_COLOR in kwargs:
                self._rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
                await light.set_rgb_color(self._rgb)
            elif ATTR_EFFECT in kwargs:
                self._attr_effect = kwargs[ATTR_EFFECT]
                effect = EFFECTS_MAPPING[self._attr_effect]
                await light.set_effect(effect)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        if not self._is_on:
            self._available = False
            return
        async with self._coordinator as light:
            await light.set_power(False)
        self._is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return

        state_attributes = {}
        if ATTR_BRIGHTNESS in state.attributes:
            self._brightness = int(state.attributes[ATTR_BRIGHTNESS] or self._brightness)
            state_attributes[ATTR_BRIGHTNESS] = self._brightness
        if ATTR_HS_COLOR in state.attributes:
            self._rgb = color_util.color_hs_to_RGB(*(state.attributes[ATTR_HS_COLOR] or self._rgb))
        if ATTR_EFFECT in state.attributes:
            self._attr_effect = state.attributes[ATTR_EFFECT] or self._attr_effect
        initialize: CoroutineType
        if state.state == "on":
            self._is_on = True
            initialize = self.async_turn_on(**state_attributes)
        else:
            self._is_on = False
            initialize = self.async_turn_off()
        self.async_write_ha_state()
        self._coordinator.create_on_connect_task(initialize)
