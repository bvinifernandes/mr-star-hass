"""Light platform for MR Star garlands."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from mr_star_ble import Effect

from . import MrStarConfigEntry
from .entity import MrStarEntity

# Names kept from the original integration so existing automations and
# scenes that select an effect by name keep working.
LEGACY_EFFECT_NAMES: dict[str, Effect] = {
    "Automatic Loop": Effect.AUTOMATIC_LOOP,
    "Symphony": Effect.SYMPHONY,
    "Fluttering": Effect.COLORFUL_FLUTTERING,
    "Open & Close": Effect.RAINBOW_OPEN_CLOSE,
    "Light & Dark Transition": Effect.RAINBOW_LIGHT_DARK_TRANSITION,
    "Flowing Water": Effect.RAINBOW_FLOWING_WATER,
}

_VOWELS = frozenset("aeiou")


def _humanize(effect: Effect) -> str:
    """Turn an enum member name into a readable effect name.

    Colour-code abbreviations such as RGB or YCP have no vowels, so they
    are kept upper case instead of being title cased into "Rgb".
    """
    words = []
    for word in effect.name.split("_"):
        if not _VOWELS & set(word.lower()):
            words.append(word.upper())
        else:
            words.append(word.capitalize())
    return " ".join(words)


def _build_effects() -> dict[str, Effect]:
    """Return every effect the device supports, keyed by display name."""
    effects = dict(LEGACY_EFFECT_NAMES)
    known = set(LEGACY_EFFECT_NAMES.values())
    for effect in Effect:
        if effect in known:
            continue
        effects[_humanize(effect)] = effect
    return effects


EFFECTS: dict[str, Effect] = _build_effects()
EFFECT_LIST: list[str] = sorted(EFFECTS)


async def async_setup_entry(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    entry: MrStarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the garland light."""
    async_add_entities([MrStarLightEntity(entry)])


class MrStarLightEntity(MrStarEntity, LightEntity, RestoreEntity):
    """The garland itself, as a light."""

    _attr_name = "Light"
    _attr_icon = "mdi:led-strip-variant"
    _attr_color_mode = ColorMode.HS
    _attr_supported_color_modes = {ColorMode.HS}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = EFFECT_LIST

    def __init__(self, entry: MrStarConfigEntry) -> None:
        """Initialise the light."""
        data = entry.runtime_data
        super().__init__(data.coordinator, data.device_info, data.address)
        self._attr_unique_id = f"{data.address}_light"
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_hs_color = (0.0, 0.0)
        self._attr_effect = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the garland on and apply any requested attributes."""
        async with self.coordinator as api:
            light = self.assert_connected(api)
            if not self._attr_is_on:
                await light.set_power(True)
                self._attr_is_on = True
            if ATTR_BRIGHTNESS in kwargs:
                brightness = int(kwargs[ATTR_BRIGHTNESS])
                await light.set_brightness(min(brightness, 255) / 255)
                self._attr_brightness = brightness
            if ATTR_HS_COLOR in kwargs:
                hue, saturation = kwargs[ATTR_HS_COLOR]
                await light.set_hs_color((int(round(hue)), float(saturation)))
                self._attr_hs_color = (float(hue), float(saturation))
            if ATTR_EFFECT in kwargs:
                name = kwargs[ATTR_EFFECT]
                effect = EFFECTS.get(name)
                if effect is None:
                    raise HomeAssistantError(f"Unknown effect: {name}")
                await light.set_effect(effect)
                self._attr_effect = name
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the garland off."""
        async with self.coordinator as api:
            light = self.assert_connected(api)
            await light.set_power(False)
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore the previous state and re-apply it once connected."""
        await super().async_added_to_hass()

        state = await self.async_get_last_state()
        if state is None:
            return

        attributes: dict[str, Any] = {}
        if brightness := state.attributes.get(ATTR_BRIGHTNESS):
            self._attr_brightness = int(brightness)
            attributes[ATTR_BRIGHTNESS] = self._attr_brightness
        if hs_color := state.attributes.get(ATTR_HS_COLOR):
            self._attr_hs_color = (float(hs_color[0]), float(hs_color[1]))
            attributes[ATTR_HS_COLOR] = self._attr_hs_color
        if (effect := state.attributes.get(ATTR_EFFECT)) and effect in EFFECTS:
            self._attr_effect = effect
            attributes[ATTR_EFFECT] = effect

        if state.state == "on":
            self._attr_is_on = True
            self.coordinator.run_when_connected(
                lambda: self._async_restore_on(attributes)
            )
        else:
            self._attr_is_on = False
            self.coordinator.run_when_connected(self.async_turn_off)

        self.async_write_ha_state()

    async def _async_restore_on(self, attributes: dict[str, Any]) -> None:
        """Re-apply the restored on-state to the device.

        The power flag is cleared first so that async_turn_on issues the
        power command as well as the attribute commands.
        """
        self._attr_is_on = False
        await self.async_turn_on(**attributes)
