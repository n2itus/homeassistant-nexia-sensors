# Nexia Room IQ Sensors for Home Assistant

This custom integration adds support for Nexia/Trane/American Standard Room IQ sensors to Home Assistant. It creates individual sensor entities for temperature, humidity, battery level, and zone weight for each Room IQ sensor in your system.

**Key Feature:** Automatically requests fresh sensor data every 2 minutes from your physical thermostat, ensuring your Room IQ sensors always display current readings instead of stale cached data.

## Features

- **Temperature sensors** - Individual temperature readings from each Room IQ sensor
- **Humidity sensors** - Individual humidity readings from each Room IQ sensor  
- **Battery sensors** - Battery level monitoring for wireless Room IQ sensors
- **Weight sensors** - Shows each sensor's contribution to the zone's weighted average temperature
- **Automatic fresh data requests** - Polls physical thermostat every 2 minutes for current readings
- **Automatic discovery** - Finds all Room IQ sensors automatically
- **Clean integration** - Sensors grouped under your zone device in Home Assistant
- **Automatic setup** - No manual reload needed after Home Assistant restarts

## Prerequisites

- Home Assistant with the built-in Nexia integration already configured and working
- Access to your Home Assistant configuration directory
- Room IQ sensors paired with your Nexia/Trane thermostat

## Installation

### Step 1: Access Your Configuration Files

You can use any of these methods:
- **File Editor** add-on (Settings → Add-ons → File Editor)
- **Studio Code Server** add-on (Settings → Add-ons → Studio Code Server)
- **Samba Share** add-on (access via network share)
- **SSH & Terminal** add-on (for advanced users)

### Step 2: Create the Directory Structure

Create a new folder: `/config/custom_components/nexia_roomiq/`

**Using File Editor or Studio Code Server:**
1. Navigate to your `/config/` folder
2. Create a new folder called `custom_components` (if it doesn't exist)
3. Inside `custom_components`, create a new folder called `nexia_roomiq`

### Step 3: Copy the 4 Required Files

Create these 4 files inside `/config/custom_components/nexia_roomiq/`:

1. **`__init__.py`** - Copy content from the "__init__.py" artifact
2. **`const.py`** - Copy content from the "const.py" artifact  
3. **`manifest.json`** - Copy content from the "manifest.json" artifact
4. **`sensor.py`** - Copy content from the "sensor.py" artifact


### Step 4: Verify Directory Structure

Your final structure should look like:

```
/config/
└── custom_components/
    └── nexia_roomiq/
        ├── __init__.py
        ├── const.py
        ├── manifest.json
        └── sensor.py
```

### Step 5: Enable the Integration

Edit your `configuration.yaml` file (in `/config/` folder) and add this line:

```yaml
nexia_roomiq:
```

**Tip:** Add it at the end of the file on a new line.

### Step 6: Restart Home Assistant

1. Go to **Settings → System → Restart**
2. Click **Restart Home Assistant**
3. Wait for the system to restart (usually 1-2 minutes)

### Step 7: Wait for Automatic Setup

After Home Assistant restarts:
1. The integration will automatically detect the Nexia integration (waits ~3 seconds)
2. Inject the Room IQ sensor code
3. Reload the Nexia integration automatically
4. Your Room IQ sensors will appear and start updating

**This happens automatically** - no manual steps needed!

### Step 8: Verify

1. Go to **Settings → Devices & Services**
2. Click on **Nexia** integration
3. Click on your zone device (e.g., "Downstairs NativeZone")
4. You should see your new Room IQ sensors

The sensors will update every 2 minutes with fresh data from your thermostat!

## What Gets Created

The integration creates sensors for each Room IQ device in your system.

### Example: 4 Room IQ Sensors

**Built-in Thermostat Sensor:**
- `sensor.thermostat_1_zone_1_roomiq_thermostat_1_temperature` → "Thermostat 1 Temperature"
- `sensor.thermostat_1_zone_1_roomiq_thermostat_1_humidity` → "Thermostat 1 Humidity"
- `sensor.thermostat_1_zone_1_roomiq_thermostat_1_weight` → "Thermostat 1 RoomIQ Weight"

**Wireless Room IQ Sensors (×3):**

For each wireless sensor (e.g., "Room 1"):
- `sensor.thermostat_1_zone_1_roomiq_room_1_temperature` → "Room 1 Temperature"
- `sensor.thermostat_1_zone_1_roomiq_room_1_humidity` → "Room 1 Humidity"
- `sensor.thermostat_1_zone_1_roomiq_room_1_battery` → "Room 1 Battery"
- `sensor.thermostat_1_zone_1_roomiq_room_1_weight` → "Room 1 RoomIQ Weight"

**Total:** 15 new entities for a system with 4 Room IQ sensors (1 built-in + 3 wireless)

### Entity Naming

- **Entity IDs** are long and descriptive for uniqueness
- **Display names** are short and clean (just sensor name + type)
- All sensors are grouped under your zone device for organization

## Understanding the Sensors

### Temperature Sensor
- **Device Class:** Temperature
- **Unit:** °F or °C (matches your thermostat settings)
- **State:** Current temperature reading

### Humidity Sensor  
- **Device Class:** Humidity
- **Unit:** %
- **State:** Current humidity percentage

### Battery Sensor
- **Device Class:** Battery
- **Unit:** %
- **State:** Current battery level
- **Note:** Only created for wireless Room IQ sensors

### Weight Sensor
- **Device Class:** None
- **State Class:** Measurement
- **Unit:** None (dimensionless ratio)
- **State:** Sensor's contribution to zone average

**Understanding Weight Values:**

The weight sensor shows how much each Room IQ sensor contributes to your zone's weighted average temperature:

- **1.0** = Only this sensor is active (100% weight)
- **0.5** = This sensor + 1 other active (50% each)
- **0.33** = This sensor + 2 others active (33% each)
- **0.25** = All 4 sensors active (25% each)
- **0.0** = This sensor is NOT included in zone average

You control which sensors are active through the Nexia app or automations. The weight values update automatically based on your selections.

### Sensor Attributes

Each sensor includes these attributes (viewable in the entity details):

**All Sensors:**
- `sensor_id` - Unique ID from Nexia API
- `sensor_name` - Display name (e.g., "Room 1")
- `sensor_type` - "thermostat" or "930" (wireless model number)
- `serial_number` - Device serial number
- `weight` - Current weight value (also available as separate sensor)
- `temperature` - Current temperature (on non-temperature sensors)
- `humidity` - Current humidity (on non-humidity sensors)

**Wireless Sensors Only:**
- `connected` - Connection status (true/false)
- `battery_level` - Battery percentage
- `battery_low` - Low battery warning (true/false)

## How It Works

### Data Refresh Mechanism

The Nexia cloud API typically caches Room IQ sensor data, which can be hours old. This integration solves that problem:

1. **Every 2 minutes** (Home Assistant's default Nexia update interval):
   - Calls `zone.load_current_sensor_state()` on each zone
   - This requests the physical thermostat to upload fresh sensor data to the cloud
   - Waits 5 seconds for the data to reach the cloud (based on mobile app behavior)
   - Fetches the now-fresh data from the Nexia cloud
   - Updates all Room IQ sensor entities

This ensures your Room IQ sensors always show current readings instead of stale cached data.

### Integration Architecture

This integration:
- Depends on the built-in Nexia integration
- Injects additional sensor creation into Nexia's sensor platform
- Uses the same data coordinator as the main Nexia integration
- Wraps the coordinator's update method to request fresh data
- Creates entities alongside existing Nexia entities
- Automatically activates on Home Assistant startup

### Logging

The integration uses appropriate log levels:
- **INFO**: Startup messages and when sensors are initially added
- **WARNING**: Non-critical issues (e.g., failed to request fresh data from a zone)
- **ERROR**: Critical failures (e.g., Nexia integration not found)
- **DEBUG**: Routine operations (update cycles, data requests) - only visible when debug logging is enabled

**To enable debug logging (recommended method):**
1. Go to **Settings → Devices & Services**
2. Find **Nexia Room IQ Sensors** or **Nexia** integration
3. Click the **three dots (⋮)** in the upper right corner
4. Select **Enable debug logging**
5. Reproduce the issue or wait for update cycles
6. Click **Disable debug logging** when done
7. Click **Download diagnostics** to save the debug log

**No restart required!** This is much easier than editing `configuration.yaml`.

Alternatively, you can enable debug logging in `configuration.yaml` (requires restart):
```yaml
logger:
  default: info
  logs:
    custom_components.nexia_roomiq: debug
```

## Troubleshooting

### Sensors Not Appearing

1. **Verify the integration loaded:**
   
   Go to **Settings → System → Logs** and look for:
   ```
   Nexia Room IQ Sensors integration starting
   Nexia Room IQ Sensors setup complete
   Adding X Room IQ sensor entities
   ```

2. **If you only see "integration starting" but nothing else:**
   - Wait 30 seconds for automatic setup to complete
   - Check for errors in the logs
   - Verify Nexia integration is working

3. **Enable debug logging using the UI method above** to see detailed operation

4. **Verify Room IQ data exists:**
   - Settings → Devices & Services → Nexia
   - Click three dots → Download diagnostics
   - Open the downloaded file and search for "room_iq_sensors"
   - Confirm sensors are listed with valid data

5. **Clear cache (if using Studio Code Server or Terminal add-on):**
   - Delete the `__pycache__` folder inside `/config/custom_components/nexia_roomiq/`
   - Restart Home Assistant

6. **Verify files are correct:**
   - Open each file in File Editor or Studio Code Server
   - Make sure they have content (not empty)
   - Check for any error messages in the editor

### Common Issues

**"Nexia integration not found"**
- The main Nexia integration isn't set up
- Solution: Configure Nexia in Settings → Devices & Services first

**Sensors show "unavailable" after restart**
- The integration may still be setting up (wait 30 seconds)
- If persists after 1 minute, check logs for errors
- Solution: Try manually reloading Nexia integration once

**Sensors show stale/old data**
- The fresh data request mechanism may not be working
- Enable DEBUG logging to see if `load_current_sensor_state()` is being called
- Check logs for warnings about failed data requests

**Changes to sensor.py not taking effect**
- Python module cache not cleared
- Solution: 
  - Using File Editor/Studio Code Server: Delete the `__pycache__` folder if it exists
  - Do a FULL restart (Settings → System → Restart), not just reload
  - If `__pycache__` folder keeps appearing, delete it and restart again

**Entity names too long**
- This is expected for entity IDs (they must be unique)
- Display names are short - check the entity card in UI
- Entity IDs: `sensor.downstairs_nativezone_roomiq_living_room_temperature`
- Display names: "Living Room Temperature"

**Sensors not updating every 2 minutes**
- Enable DEBUG logging to verify wrapper is being called
- Check for warnings in logs about failed requests
- Verify Nexia integration is working and updating normally

## Updating

When Home Assistant updates, this custom integration should continue working unless the Nexia integration's internal structure changes significantly.

To update the custom component:
1. Open the files in File Editor or Studio Code Server
2. Replace the content with updated versions
3. Delete the `__pycache__` folder if it exists (inside `/config/custom_components/nexia_roomiq/`)
4. Restart Home Assistant (Settings → System → Restart)

## Uninstalling

1. Remove `nexia_roomiq:` from `configuration.yaml`
2. Restart Home Assistant  
3. Delete `/config/custom_components/nexia_roomiq/` directory
4. Restart again to clean up entities

## Technical Details

- **Integration Type:** Custom component (YAML configuration)
- **Dependencies:** Built-in Nexia integration
- **Data Source:** Nexia API via nexia-python library
- **Update Method:** Polling (every 120 seconds / 2 minutes)
- **Fresh Data Mechanism:** Calls `zone.load_current_sensor_state()` before each poll
- **Data Storage:** None (reads from Nexia's runtime data)

## Support & Contributions

This integration was created to expose Room IQ sensor data that's already downloaded by the Nexia integration but not exposed as individual entities, and to solve the stale data problem by actively requesting fresh sensor readings.

For issues:
- Check Home Assistant logs with debug logging enabled (use UI method)
- Verify diagnostics data contains room_iq_sensors
- Ensure main Nexia integration is working properly
- Try clearing cache and doing a full restart

## Credits

Created to fill the gap in Home Assistant's Nexia integration Room IQ sensor support and ensure fresh sensor data.

## License

MIT License - Free to use and modify
