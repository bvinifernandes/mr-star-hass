# Changelog

## 2.0.0

Compatibility and correctness release. Requires Home Assistant 2026.3 or newer.

### Fixed

- The integration no longer fails to load on Home Assistant 2026.3 and later.
  It imported `COLOR_MODE_HS`, which was removed along with the rest of the
  deprecated `COLOR_MODE_*` and `SUPPORT_*` light constants.
- The light declared three different colour mode answers: a class attribute of
  `{XY, BRIGHTNESS}`, a property returning `{HS}`, and a colour mode of `HS`. It
  now declares hue and saturation once, which is what the firmware accepts.
- Unloading or reloading a config entry no longer hangs when the garland is out
  of range. The session task ignored stop requests while it was in its
  reconnect backoff, and only signalled completion on the clean path.
- The config flow no longer reports success for a garland it could not reach.
  Its connection check swallowed every exception and returned a value the
  caller discarded, which made the error branches and their translated strings
  unreachable.
- Restoring a light after a restart now re-applies brightness, colour and
  effect. The restored values were parsed and then passed to the turn-on call
  as an empty dictionary.
- Turning off an already-off light no longer marks the entity unavailable.
  Availability follows the Bluetooth session, not the power state.
- The LED count entity no longer raises `TypeError` when it is restored with no
  previous value.
- Entity unique IDs are derived from the full Bluetooth address instead of a
  display name built from the last two bytes, which could collide between
  devices. Existing entities are migrated on upgrade, so history is kept.

### Changed

- Connections go through `bleak_retry_connector` instead of a bare
  `BleakClient`, which adds retries and support for ESPHome Bluetooth proxies.
  A device that is not in range is now detected before a connection is
  attempted.
- Connection state is pushed to the entities when it changes, replacing the
  five second poll. The integration is push-based, so there was nothing to poll.
- The full effect list reported by the firmware is exposed, 62 effects instead
  of 6. The six original effect names are preserved, so existing automations
  and scenes keep working.
- Colours are sent as hue and saturation directly, removing a lossy conversion
  through RGB.
- `mr_star_ble` updated to 0.4.1, in which `MrStarLight` became `MrStarAPI`.
- Config entry state moved to `entry.runtime_data`, and platform setup, device
  info and entity naming follow current Home Assistant patterns.
- Development requirements, the Makefile and CI target Python 3.14 and Home
  Assistant 2026.9.3. A test suite was added and runs in CI.
