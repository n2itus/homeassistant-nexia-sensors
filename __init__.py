"""The Nexia Room IQ Sensors integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nexia_roomiq"
NEXIA_DOMAIN = "nexia"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Nexia Room IQ Sensors component."""
    _LOGGER.info("Nexia Room IQ Sensors integration starting")
    
    # Wait a bit to ensure Nexia integration has loaded
    await asyncio.sleep(3)
    
    try:
        # Check if Nexia has config entries
        nexia_entries = hass.config_entries.async_entries(NEXIA_DOMAIN)
        if not nexia_entries:
            _LOGGER.error("No Nexia integration found. Please set up Nexia first.")
            return False
        
        _LOGGER.debug("Found Nexia integration, injecting Room IQ sensor setup")
        
        import homeassistant.components.nexia.sensor as nexia_sensor
        from .sensor import inject_roomiq_sensors
        
        inject_roomiq_sensors(nexia_sensor)
        
        # Reload Nexia to activate the injection
        _LOGGER.debug("Reloading Nexia integration to activate Room IQ sensors")
        for entry in nexia_entries:
            await hass.config_entries.async_reload(entry.entry_id)
        
        _LOGGER.info("Nexia Room IQ Sensors setup complete")
        return True
        
    except Exception as err:
        _LOGGER.error("Failed to set up Room IQ sensors: %s", err, exc_info=True)
        return False



