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
    
    # Setup initial tracking
    await async_setup_tracking(hass, entry)
    
    # Tie the update listener to the integration's option updates
    entry.async_on_unload(entry.add_update_listener(async_update_options_listener))
    
    return True

async def async_setup_tracking(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up or rebuild the state tracking listener based on data and options."""
    # If a previous listener exists, clean it up before building the new one
    if entry.entry_id in hass.data[DOMAIN] and "unsub" in hass.data[DOMAIN][entry.entry_id]:
        hass.data[DOMAIN][entry.entry_id]["unsub"]()
        _LOGGER.debug("Cleaned up old Lackey Hub state listener.")

    host = entry.data["host"]
    port = entry.data["port"]
    token = entry.data["token"]
    
    # Check entry.options first (from options flow), fall back to entry.data (initial setup)
    alarm_entity = entry.options.get("alarm_entity", entry.data.get("alarm_entity"))
    weather_entity = entry.options.get("weather_entity", entry.data.get("weather_entity"))
    door_sensors = entry.options.get("door_sensors", entry.data.get("door_sensors", []))
    
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

    # Attach the listener to only watch the updated list of entities
    unsub = async_track_state_change_event(
        hass, tracked_entities, async_state_changed_listener
    )
    
    hass.data[DOMAIN][entry.entry_id] = {"unsub": unsub}
    _LOGGER.info("Lackey Hub is tracking %d entities", len(tracked_entities))

async def async_update_options_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options flow update by rebuilding the event tracking."""
    _LOGGER.info("Lackey Hub entity options updated. Rebuilding state tracking...")
    await async_setup_tracking(hass, entry)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.entry_id in hass.data[DOMAIN]:
        # Unsubscribe the live event listener if it exists
        if "unsub" in hass.data[DOMAIN][entry.entry_id]:
            hass.data[DOMAIN][entry.entry_id]["unsub"]()
        hass.data[DOMAIN].pop(entry.entry_id)
    return True
