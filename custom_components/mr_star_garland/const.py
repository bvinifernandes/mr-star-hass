"""Constants for the MR Star Garland integration."""

from typing import Final

DOMAIN: Final = "mr_star_garland"

# How long a BLE session is held open before it is recycled, in seconds.
SESSION_TTL_SECONDS: Final = 120
# Timeout applied to a single connection attempt, in seconds.
CONNECTION_TIMEOUT_SECONDS: Final = 30
# Delay before retrying after a failed connection attempt, in seconds.
RECONNECT_BACKOFF_SECONDS: Final = 15
# Upper bound on how long unloading waits for the session task to finish.
STOP_TIMEOUT_SECONDS: Final = 10

# LED count limits accepted by the device firmware.
DEFAULT_LED_COUNT: Final = 40
MIN_LED_COUNT: Final = 8
MAX_LED_COUNT: Final = 300
