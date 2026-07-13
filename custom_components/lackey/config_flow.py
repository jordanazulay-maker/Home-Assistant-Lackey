"""Config flow for Lackey Hub integration."""
import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

DOMAIN = "lackey"
_LOGGER = logging.getLogger(__name__)

class LackeyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lackey Hub."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._host = None
        self._port = None
        self.setup_data = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow handler for reconfiguration."""
        return LackeyOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step when a user manually clicks 'Add Integration'."""
        errors = {}
        
        if user_input is not None:
            self._host = user_input["host"]
            self._port = user_input["port"]
            
            await self.async_set_unique_id(self._host)
            self._abort_if_unique_id_configured()
            
            return await self.async_step_pair()

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
        
        await self.async_set_unique_id(self._host)
        self._abort_if_unique_id_configured()
        
        self.context["title_placeholders"] = {"name": "Lackey Hub"}
        
        return await self.async_step_pair()

    async def async_step_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm the discovery and ask for the pairing PIN."""
        errors = {}

        if user_input is not None:
            pin = user_input["pin"]
            try:
                session = async_get_clientsession(self.hass)
                url = f"https://{self._host}:{self._port}/setup"
                
                async with session.post(url, json={"pin": pin}, ssl=False) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success"):
                            self.setup_data = {
                                "host": self._host,
                                "port": self._port,
                                "token": data.get("deviceToken")
                            }
                            return await self.async_step_entities()
                        else:
                            errors["base"] = "invalid_pin"
                    elif resp.status == 401:
                        errors["base"] = "invalid_pin"
                    else:
                        errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error("Error connecting to Lackey Hub: %s", e)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="pair", 
            data_schema=vol.Schema({
                vol.Required("pin"): str
            }),
            errors=errors,
            description_placeholders={"name": "Lackey Hub"}
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Second step: Let the user select their entities."""
        if user_input is not None:
            self.setup_data.update(user_input)
            return self.async_create_entry(title="Lackey Hub", data=self.setup_data)

        data_schema = vol.Schema({
            vol.Required("alarm_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="alarm_control_panel")
            ),
            vol.Optional("door_sensors"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
            ),
            vol.Optional("lights"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["light", "switch"], multiple=True)
            ),
        })

        return self.async_show_form(
            step_id="entities", 
            data_schema=data_schema
        )


class LackeyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options reconfiguration for Lackey Hub."""

    # Note: __init__ removed entirely to let the HA base class handle config_entry safely.

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the configuration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = {}

        # Safely pull existing values from self.config_entry via base class property
        current_alarm = self.config_entry.options.get("alarm_entity", self.config_entry.data.get("alarm_entity"))
        if current_alarm:
            options_schema[vol.Required("alarm_entity", default=current_alarm)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="alarm_control_panel")
            )
        else:
            options_schema[vol.Required("alarm_entity")] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="alarm_control_panel")
            )

        current_doors = self.config_entry.options.get("door_sensors", self.config_entry.data.get("door_sensors"))
        if current_doors:
            options_schema[vol.Optional("door_sensors", default=current_doors)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
            )
        else:
            options_schema[vol.Optional("door_sensors")] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
            )

        current_lights = self.config_entry.options.get("lights", self.config_entry.data.get("lights"))
        if current_lights:
            options_schema[vol.Optional("lights", default=current_lights)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["light", "switch"], multiple=True)
            )
        else:
            options_schema[vol.Optional("lights")] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["light", "switch"], multiple=True)
            )

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options_schema))
