"""Initialize the Lackey Hub integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN = "lackey"
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lackey Hub from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Grab the saved connection details and token
    host = entry.data["host"]
    port = entry.data["port"]
    token = entry.data["token"]
    
    # Gather the user's custom entity selections from the config flow UI
    alarm_entity = entry.data.get("alarm_entity")
    weather_entity = entry.data.get("weather_entity")
    door_sensors = entry.data.get("door_sensors", [])
    
    # Combine them into a single master list to monitor
    tracked_entities = []
    if alarm_entity:
        tracked_entities.append(alarm_entity)
    if weather_entity:
        tracked_entities.append(weather_entity)
    if door_sensors:
        tracked_entities.extend(door_sensors)
        
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

    # Attach the listener to only watch the user's custom selected entities
    unsub = async_track_state_change_event(
        hass, tracked_entities, async_state_changed_listener
    )
    
    # Tie the listener's lifespan to the integration
    entry.async_on_unload(unsub)
    
    hass.data[DOMAIN][entry.entry_id] = {"unsub": unsub}
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)
    return True
