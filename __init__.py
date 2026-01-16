#Custom component to expose individual Nexia RoomIQ sensor temperatures
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    #Set up the Nexia RoomIQ Sensors component
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    #et up from a config entry — not used here, but required for future-proofing.
    return True
