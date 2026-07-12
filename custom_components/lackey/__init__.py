"""Initialize the Lackey Hub integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN = "lackey"
_LOGGER = logging.getLogger(__name__)

# The exact entities the Hub needs to know about
TRACKED_ENTITIES = [
    "alarm_control_panel.alarmo",
    "weather.home",
    "binary_sensor.front_door_door",
    "binary_sensor.back_door_door",
    "binary_sensor.contact_sensor_door",
    "binary_sensor.contact_sensor_door_2",
    "binary_sensor.main_guest_door",
    "binary_sensor.french_door_door",
    "binary_sensor.french_ii_door",
    "binary_sensor.guest_room_door"
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lackey Hub from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Grab the saved connection details from the config flow pairing
    host = entry.data["host"]
    port = entry.data["port"]
    token = entry.data["token"]
    
    session = async_get_clientsession(hass)
    hub_url = f"https://{host}:{port}/api/ha/state_update"

    async def async_state_changed_listener(event: Event) -> None:
        """Listen for state changes and instantly push them to the Hub."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        payload = {
            "entity_id": new_state.entity_id,
            "state": new_state.state,
            "attributes": dict(new_state.attributes)
        }
        
        try:
            # ssl=False is required because the Hub uses a self-signed local cert
            await session.post(
                hub_url, 
                json=payload, 
                headers={"x-device-token": token},
                ssl=False
            )
            _LOGGER.debug("Pushed %s state to Lackey Hub", new_state.entity_id)
        except Exception as e:
            _LOGGER.error("Failed to push state to Lackey Hub: %s", e)

    # Attach the listener to Home Assistant's event bus
    unsub = async_track_state_change_event(
        hass, TRACKED_ENTITIES, async_state_changed_listener
    )
    
    # Tie the listener's lifespan to the integration so it cleans up if uninstalled
    entry.async_on_unload(unsub)
    
    hass.data[DOMAIN][entry.entry_id] = {"unsub": unsub}
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)
    return True
