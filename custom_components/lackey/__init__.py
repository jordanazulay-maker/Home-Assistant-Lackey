import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr

DOMAIN = "lackey"
_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lackey Hub from a config entry."""
    host = entry.data["host"]
    port = entry.data.get("port", 8443)
    token = entry.data["token"]
    
    session = async_get_clientsession(hass)

    # 1. Register the physical device in Home Assistant
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, host)},
        name="Lackey Hub",
        manufacturer="Blindshome",
        model="ACP Gateway",
        sw_version="1.0.0",
        configuration_url=f"https://{host}:41921"
    )

    # 2. Build the 30-second polling engine
    async def async_update_data():
        """Fetch data from the hub's API."""
        try:
            url = f"https://{host}:{port}/api/features/state"
            headers = {"x-device-token": token}
            
            async with session.get(url, headers=headers, ssl=False) as response:
                if response.status != 200:
                    raise UpdateFailed(f"API Error: {response.status}")
                return await response.json()
        except Exception as err:
            raise UpdateFailed(f"Communication error: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="lackey_hub",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    # Fetch initial data straight away so it doesn't load empty
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 3. Hand off control to our sensors file
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
