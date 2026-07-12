"""Config flow for Lackey Hub integration."""
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class LackeyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lackey Hub."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step when a user manually clicks 'Add Integration'."""
        # If they haven't submitted anything yet, just show a blank form for now.
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema({})
            )

        # Later, we will replace this with our auto-pairing logic!
        return self.async_create_entry(title="Lackey Hub", data=user_input)
