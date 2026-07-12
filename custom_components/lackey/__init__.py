"""The Lackey Hub integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lackey Hub from a config entry."""
    _LOGGER.info("Setting up Lackey Hub integration")
    
    # This creates a safe space in Home Assistant's memory for our hub's data
    hass.data.setdefault(DOMAIN, {})
    
    # Later, we will add the code here to maintain the connection to your Pi
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Lackey Hub integration")
    
    # Later, we will add cleanup logic here for when a user deletes the integration
    
    return True
