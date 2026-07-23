"""The Lackey Hub integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN = "lackey"
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lackey Hub from a config entry. Runs on HA startup."""
    hass.data.setdefault(DOMAIN, {})
    
    # Store the integration data in HA's memory
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Instantly push the saved lists to the Node.js hub!
    await async_sync_entities_to_hub(hass, entry)
    
    # Listen for whenever the user clicks "Configure" and changes their lists
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update when the user changes their selected entities."""
    # When the menu is saved, re-push the newly selected lists to the hub
    await async_sync_entities_to_hub(hass, entry)

async def async_sync_entities_to_hub(hass: HomeAssistant, entry: ConfigEntry):
    """Securely push the configured entities to the Node.js backend."""
    
    # Options (changed via Configure menu) take priority over Data (initial setup)
    alarm_entity = entry.options.get("alarm_entity", entry.data.get("alarm_entity"))
    door_sensors = entry.options.get("door_sensors", entry.data.get("door_sensors", []))
    lights = entry.options.get("lights", entry.data.get("lights", []))
    
    host = entry.data.get("host")
    port = entry.data.get("port")
    token = entry.data.get("token")
    
    if not host or not port or not token:
        _LOGGER.error("Lackey Hub is missing connection details. Cannot sync.")
        return
        
    url = f"https://{host}:{port}/api/ha/sync_entities"
    headers = {"x-device-token": token}
    payload = {
        "alarm_entity": alarm_entity,
        "door_sensors": door_sensors,
        "lights": lights
    }
    
    try:
        # Ask HA for a session that explicitly ignores SSL verification
        session = async_get_clientsession(hass, verify_ssl=False)
        
        # Now fire the payload!
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 200:
                _LOGGER.info("Successfully synced HA configuration to Lackey Hub!")
            else:
                _LOGGER.error("Failed to sync config to Lackey Hub. Status: %s", resp.status)
    except Exception as e:
        _LOGGER.error("Error communicating with Lackey Hub: %s", e)
