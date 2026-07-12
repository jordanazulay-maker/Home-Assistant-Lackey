"""Config flow for Lackey Hub integration."""
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.components.zeroconf import ZeroconfServiceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class LackeyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lackey Hub."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._host = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step when a user manually clicks 'Add Integration'."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema({})
            )

        return self.async_create_entry(title="Lackey Hub", data=user_input)

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery from the Pi."""
        self._host = discovery_info.host
        
        # Prevent Home Assistant from discovering the same Pi twice
        await self.async_set_unique_id(self._host)
        self._abort_if_unique_id_configured()
        
        # Prepare the UI notification with the device's hostname
        self.context["title_placeholders"] = {"name": discovery_info.hostname}
        
        # Move directly to the confirmation step
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm the discovery in the Home Assistant UI."""
        if user_input is not None:
            # The user clicked "Submit" in the UI. Create the integration!
            return self.async_create_entry(
                title="Lackey Hub", 
                data={"host": self._host}
            )

        # Show a simple pop-up asking the user to confirm the connection
        return self.async_show_form(
            step_id="confirm", 
            data_schema=vol.Schema({})
        )
