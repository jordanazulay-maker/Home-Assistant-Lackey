"""Config flow for Lackey Hub integration."""
import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# Hardcoding the domain so we don't need a separate const.py file!
DOMAIN = "lackey"
_LOGGER = logging.getLogger(__name__)

class LackeyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lackey Hub."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._host = None
        self._port = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step when a user manually clicks 'Add Integration'."""
        errors = {}
        
        if user_input is not None:
            self._host = user_input["host"]
            self._port = user_input["port"]
            
            # Prevent duplicates
            await self.async_set_unique_id(self._host)
            self._abort_if_unique_id_configured()
            
            # Jump directly to the PIN pairing screen
            return await self.async_step_pair()

        # Show a form asking for IP and Port
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host", default="192.168.68.53"): str,
                vol.Required("port", default=8443): int,
            }),
            errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery from the Pi."""
        self._host = discovery_info.host
        self._port = discovery_info.port
        
        # Prevent Home Assistant from discovering the same Pi twice
        await self.async_set_unique_id(self._host)
        self._abort_if_unique_id_configured()
        
        # Prepare the UI notification with the device's name
        self.context["title_placeholders"] = {"name": "Lackey Hub"}
        
        # Move directly to the pairing step asking for the PIN
        return await self.async_step_pair()

    async def async_step_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm the discovery and ask for the pairing PIN."""
        errors = {}

        if user_input is not None:
            pin = user_input["pin"]
            try:
                # Use HA's built-in client session wrapper for web requests
                session = async_get_clientsession(self.hass)
                url = f"https://{self._host}:{self._port}/setup"
                
                # ssl=False is needed because the hub uses a self-signed local cert
                async with session.post(url, json={"pin": pin}, ssl=False) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success"):
                            # Success! Save the deviceToken HA can use forever
                            return self.async_create_entry(
                                title="Lackey Hub",
                                data={
                                    "host": self._host,
                                    "port": self._port,
                                    "token": data.get("deviceToken")
                                }
                            )
                        else:
                            errors["base"] = "invalid_pin"
                    else:
                        errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error("Error connecting to Lackey Hub: %s", e)
                errors["base"] = "cannot_connect"

        # Show the form asking for the 8-digit PIN
        return self.async_show_form(
            step_id="pair", 
            data_schema=vol.Schema({
                vol.Required("pin"): str
            }),
            errors=errors,
            description_placeholders={"name": "Lackey Hub"}
        )
