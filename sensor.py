"""Support for Nexia Room IQ Sensors."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, TYPE_CHECKING

from nexia.const import UNIT_CELSIUS

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Import from the main Nexia integration
from homeassistant.components.nexia.coordinator import NexiaDataUpdateCoordinator
from homeassistant.components.nexia.entity import NexiaThermostatZoneEntity

_LOGGER = logging.getLogger(__name__)

# Store the original setup function and update method
_original_async_setup_entry = None
_original_update_method = {}
_injection_complete = False  # Flag to prevent re-injection

# The key used in hass.data for the coordinator
NEXIA_DOMAIN = "nexia"
UPDATE_COORDINATOR = "update_coordinator"


def inject_roomiq_sensors(nexia_sensor_module):
    """Inject Room IQ sensor setup into the Nexia sensor platform."""
    global _original_async_setup_entry, _injection_complete
    
    # Prevent re-injection if already done
    if _injection_complete:
        _LOGGER.debug("Room IQ sensor setup already injected, skipping")
        return
    
    # Save the original setup function
    _original_async_setup_entry = nexia_sensor_module.async_setup_entry
    
    # Replace with our wrapper
    nexia_sensor_module.async_setup_entry = _async_setup_entry_wrapper
    
    _injection_complete = True
    _LOGGER.debug("Room IQ sensor setup injection complete")


async def _async_setup_entry_wrapper(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Wrapper that calls original setup then adds Room IQ sensors."""
    # First call the original Nexia sensor setup
    if _original_async_setup_entry:
        await _original_async_setup_entry(hass, config_entry, async_add_entities)
    
    # Now add our Room IQ sensors
    _LOGGER.debug("Adding Room IQ sensors to Nexia integration")
    
    # Small delay to ensure Nexia data is populated
    await asyncio.sleep(0.5)
    
    await async_setup_roomiq_sensors(hass, config_entry, async_add_entities)


async def async_setup_roomiq_sensors(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Room IQ sensors for a Nexia device."""
    _LOGGER.debug("Setting up Room IQ sensors for config entry: %s", config_entry.title)
    
    # Get the coordinator from config_entry.runtime_data (new HA pattern)
    try:
        coordinator: NexiaDataUpdateCoordinator = config_entry.runtime_data
        _LOGGER.debug("Successfully got Nexia coordinator from runtime_data")
    except (AttributeError, KeyError) as err:
        _LOGGER.error(
            "Could not find Nexia coordinator in runtime_data for entry %s: %s",
            config_entry.entry_id,
            err
        )
        return
    
    nexia_home = coordinator.nexia_home
    
    # Wrap the coordinator's update method to request fresh Room IQ data
    if id(coordinator) not in _original_update_method:
        _LOGGER.debug("Wrapping coordinator update method to request fresh Room IQ data")
        _LOGGER.debug("Coordinator ID: %s", id(coordinator))
        
        # Save original method
        _original_update_method[id(coordinator)] = coordinator._async_update_data
        _LOGGER.debug("Original update method saved: %s", coordinator._async_update_data)
        
        async def _update_with_roomiq_refresh():
            """Update method that requests fresh Room IQ data first."""
            _LOGGER.debug("Room IQ refresh wrapper called - requesting fresh sensor data")
            try:
                # Request fresh sensor data from each zone
                for thermostat_id in nexia_home.get_thermostat_ids():
                    thermostat = nexia_home.get_thermostat_by_id(thermostat_id)
                    for zone_id in thermostat.get_zone_ids():
                        zone = thermostat.get_zone_by_id(zone_id)
                        try:
                            # Use load_current_sensor_state to request fresh data from physical thermostat
                            _LOGGER.debug(
                                "Requesting fresh Room IQ data from physical thermostat for zone: %s",
                                zone.get_name()
                            )
                            # This tells the physical thermostat to send fresh sensor data to the cloud
                            await zone.load_current_sensor_state()
                            _LOGGER.debug("Fresh data request sent for zone: %s", zone.get_name())
                        except Exception as zone_err:
                            _LOGGER.warning(
                                "Could not request fresh Room IQ data for zone %s: %s",
                                zone.get_name(),
                                zone_err,
                                exc_info=True
                            )
                
                # Wait for the thermostat to upload fresh Room IQ data to the cloud
                # Based on mobile app behavior, Room IQ takes 3-5 seconds to update
                _LOGGER.debug("Waiting 5 seconds for fresh Room IQ data to reach cloud...")
                await asyncio.sleep(5)
                
            except Exception as err:
                _LOGGER.warning("Error in Room IQ refresh wrapper: %s", err, exc_info=True)
            
            # Call the original update method to fetch the now-fresh data from cloud
            _LOGGER.debug("Calling original coordinator update method")
            result = await _original_update_method[id(coordinator)]()
            _LOGGER.debug("Coordinator update completed")
            return result
        
        coordinator._async_update_data = _update_with_roomiq_refresh
        _LOGGER.debug("Coordinator update method successfully wrapped")
    else:
        _LOGGER.debug("Coordinator already wrapped (ID: %s)", id(coordinator))

    entities: list[SensorEntity] = []

    # Add Room IQ sensors for each zone
    for thermostat_id in nexia_home.get_thermostat_ids():
        thermostat = nexia_home.get_thermostat_by_id(thermostat_id)

        for zone_id in thermostat.get_zone_ids():
            zone = thermostat.get_zone_by_id(zone_id)

            _LOGGER.debug("Checking for Room IQ sensors in zone: %s", zone.get_name())
            entities.extend(_create_roomiq_sensors(coordinator, zone, thermostat))

    if entities:
        _LOGGER.info("Adding %d Room IQ sensor entities", len(entities))
    
    async_add_entities(entities)


def _create_roomiq_sensors(
    coordinator: NexiaDataUpdateCoordinator,
    zone,
    thermostat,
) -> list[NexiaRoomIQSensor]:
    """Create Room IQ sensor entities for a zone."""
    entities = []

    try:
        # Access the zone's raw JSON data to get room_iq_sensors
        zone_data = getattr(zone, "_zone_json", None)

        if zone_data is None:
            _LOGGER.debug("Could not access zone JSON data for %s", zone.get_name())
            return entities

        # Navigate through the features array to find room_iq_sensors
        features = zone_data.get("features", [])
        room_iq_feature = None

        for feature in features:
            if feature.get("name") == "room_iq_sensors":
                room_iq_feature = feature
                break

        if not room_iq_feature:
            _LOGGER.debug(
                "No room_iq_sensors feature found for zone %s", zone.get_name()
            )
            return entities

        sensors = room_iq_feature.get("sensors", [])

        if not sensors:
            _LOGGER.debug("No Room IQ sensors found for zone %s", zone.get_name())
            return entities

        _LOGGER.info(
            "Found %d Room IQ sensor(s) for zone %s",
            len(sensors),
            zone.get_name(),
        )

        for sensor_data in sensors:
            try:
                sensor_id = sensor_data.get("id")
                sensor_name = sensor_data.get("name")

                if not sensor_id or not sensor_name:
                    _LOGGER.warning("Sensor missing id or name: %s", sensor_data)
                    continue

                _LOGGER.debug(
                    "Processing Room IQ sensor: ID=%s, Name=%s",
                    sensor_id,
                    sensor_name,
                )

                # Create temperature sensor if valid
                if sensor_data.get("temperature_valid", False):
                    entities.append(
                        NexiaRoomIQSensor(
                            coordinator,
                            zone,
                            thermostat,
                            sensor_id,
                            sensor_name,
                            "temperature",
                        )
                    )
                    _LOGGER.debug(
                        "Added temperature sensor for %s: %s°F",
                        sensor_name,
                        sensor_data.get("temperature"),
                    )

                # Create humidity sensor if valid
                if sensor_data.get("humidity_valid", False):
                    entities.append(
                        NexiaRoomIQSensor(
                            coordinator,
                            zone,
                            thermostat,
                            sensor_id,
                            sensor_name,
                            "humidity",
                        )
                    )
                    _LOGGER.debug(
                        "Added humidity sensor for %s: %s%%",
                        sensor_name,
                        sensor_data.get("humidity"),
                    )

                # Create battery sensor if valid and has battery
                if sensor_data.get("has_battery", False) and sensor_data.get(
                    "battery_valid", False
                ):
                    entities.append(
                        NexiaRoomIQSensor(
                            coordinator,
                            zone,
                            thermostat,
                            sensor_id,
                            sensor_name,
                            "battery",
                        )
                    )
                    _LOGGER.debug(
                        "Added battery sensor for %s: %s%%",
                        sensor_name,
                        sensor_data.get("battery_level"),
                    )

                # Create weight sensor (always present)
                entities.append(
                    NexiaRoomIQSensor(
                        coordinator,
                        zone,
                        thermostat,
                        sensor_id,
                        sensor_name,
                        "weight",
                    )
                )
                _LOGGER.debug(
                    "Added weight sensor for %s: %s",
                    sensor_name,
                    sensor_data.get("weight", 0.0),
                )

            except Exception as err:
                _LOGGER.warning(
                    "Error creating sensors for Room IQ sensor %s: %s",
                    sensor_name if "sensor_name" in locals() else "unknown",
                    err,
                    exc_info=True,
                )

    except Exception as err:
        _LOGGER.warning(
            "Unexpected error getting Room IQ sensors for zone %s: %s",
            zone.get_name(),
            err,
            exc_info=True,
        )

    return entities


class NexiaRoomIQSensor(NexiaThermostatZoneEntity, SensorEntity):
    """Nexia Room IQ Sensor (Temperature, Humidity, Battery, or Weight)."""

    _attr_has_entity_name = True

    # Sensor type configurations
    SENSOR_CONFIGS = {
        "temperature": {
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT,
            "translation_key": "room_iq_temperature",
        },
        "humidity": {
            "device_class": SensorDeviceClass.HUMIDITY,
            "state_class": SensorStateClass.MEASUREMENT,
            "unit": PERCENTAGE,
            "translation_key": "room_iq_humidity",
        },
        "battery": {
            "device_class": SensorDeviceClass.BATTERY,
            "state_class": SensorStateClass.MEASUREMENT,
            "unit": PERCENTAGE,
            "translation_key": "room_iq_battery",
        },
        "weight": {
            "device_class": None,
            "state_class": SensorStateClass.MEASUREMENT,
            "unit": None,
            "translation_key": "room_iq_weight",
        },
    }

    def __init__(
        self,
        coordinator: NexiaDataUpdateCoordinator,
        zone,
        thermostat,
        sensor_id: int,
        sensor_name: str,
        sensor_type: str,
    ) -> None:
        """Initialize the Room IQ sensor."""
        # Initialize parent class with required unique_id
        unique_id = f"{zone.zone_id}_roomiq_{sensor_id}_{sensor_type}"
        super().__init__(coordinator, zone, unique_id)

        self._sensor_id = sensor_id
        self._sensor_name = sensor_name
        self._sensor_type = sensor_type
        self._thermostat = thermostat
        
        # Build the entity name
        # For weight, use "RoomIQ Weight" format
        # For others, just use sensor name and type
        if sensor_type == "weight":
            self._attr_name = f"{sensor_name} RoomIQ Weight"
        else:
            self._attr_name = f"{sensor_name} {sensor_type.title()}"

        # Apply configuration for this sensor type
        config = self.SENSOR_CONFIGS[sensor_type]
        self._attr_device_class = config["device_class"]
        self._attr_state_class = config["state_class"]
        self._attr_translation_key = config["translation_key"]

        # Set unit of measurement
        if sensor_type == "temperature":
            # Use thermostat's temperature unit
            if thermostat.get_unit() == UNIT_CELSIUS:
                self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            else:
                self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
        else:
            self._attr_native_unit_of_measurement = config.get("unit")

    def _get_sensor_data(self) -> dict[str, Any] | None:
        """Get the sensor data from the zone's JSON."""
        try:
            zone_data = getattr(self._zone, "_zone_json", None)
            if zone_data is None:
                return None

            features = zone_data.get("features", [])
            for feature in features:
                if feature.get("name") == "room_iq_sensors":
                    sensors = feature.get("sensors", [])
                    for sensor in sensors:
                        if sensor.get("id") == self._sensor_id:
                            return sensor
        except Exception as err:
            _LOGGER.debug(
                "Error getting sensor data for %s (ID: %s): %s",
                self._sensor_name,
                self._sensor_id,
                err,
            )
        return None

    @property
    def native_value(self) -> float | int | None:
        """Return the state of the sensor."""
        sensor_data = self._get_sensor_data()
        if sensor_data is None:
            return None

        try:
            if self._sensor_type == "temperature":
                if sensor_data.get("temperature_valid", False):
                    return sensor_data.get("temperature")
            elif self._sensor_type == "humidity":
                if sensor_data.get("humidity_valid", False):
                    return sensor_data.get("humidity")
            elif self._sensor_type == "battery":
                if sensor_data.get("battery_valid", False):
                    return sensor_data.get("battery_level")
            elif self._sensor_type == "weight":
                return sensor_data.get("weight", 0.0)
        except Exception as err:
            _LOGGER.debug(
                "Error reading %s for sensor %s: %s",
                self._sensor_type,
                self._sensor_name,
                err,
            )

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {}

        sensor_data = self._get_sensor_data()
        if sensor_data is None:
            return attrs

        try:
            attrs["sensor_id"] = self._sensor_id
            attrs["sensor_name"] = self._sensor_name
            attrs["sensor_type"] = sensor_data.get("type")
            attrs["serial_number"] = sensor_data.get("serial_number")

            # Add weight (indicates sensor's contribution to zone average)
            attrs["weight"] = sensor_data.get("weight", 0.0)

            # Add connection status for wireless sensors
            if sensor_data.get("has_online", False):
                attrs["connected"] = sensor_data.get("connected", False)

            # Add battery information for wireless sensors
            if sensor_data.get("has_battery", False):
                if sensor_data.get("battery_valid", False):
                    attrs["battery_level"] = sensor_data.get("battery_level")
                    attrs["battery_low"] = sensor_data.get("battery_low", False)

            # For non-battery sensors, include all sensor readings
            if self._sensor_type != "battery":
                if sensor_data.get("temperature_valid", False):
                    attrs["temperature"] = sensor_data.get("temperature")
                if sensor_data.get("humidity_valid", False):
                    attrs["humidity"] = sensor_data.get("humidity")

        except Exception as err:
            _LOGGER.debug(
                "Error reading attributes for sensor %s: %s",
                self._sensor_name,
                err,
            )

        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False

        sensor_data = self._get_sensor_data()
        if sensor_data is None:
            return False

        # For wireless sensors, check connection status
        if sensor_data.get("has_online", False):
            if not sensor_data.get("connected", False):
                return False

        # Weight sensor is always available if sensor data exists
        if self._sensor_type == "weight":
            return True

        # Check if the value we're tracking is valid
        try:
            if self._sensor_type == "temperature":
                return sensor_data.get("temperature_valid", False)
            elif self._sensor_type == "humidity":
                return sensor_data.get("humidity_valid", False)
            elif self._sensor_type == "battery":
                return sensor_data.get("battery_valid", False) and sensor_data.get(
                    "has_battery", False
                )
        except Exception:
            return False

        return False
