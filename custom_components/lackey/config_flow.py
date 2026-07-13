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
                            # Success! Save the deviceToken and connection details to memory
                            self.setup_data = {
                                "host": self._host,
                                "port": self._port,
                                "token": data.get("deviceToken")
                            }
                            # Transition to the entity selection screen
                            return await self.async_step_entities()
                        else:
                            errors["base"] = "invalid_pin"
                    elif resp.status == 401:
                        # Catch the security timeout/incorrect PIN directly here
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

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Second step: Let the user select their entities."""
        if user_input is not None:
            # Combine the pairing data with these entity selections
            self.setup_data.update(user_input)
            
            # Now we officially create the integration!
            return self.async_create_entry(title="Lackey Hub", data=self.setup_data)

        # Build the dynamic UI dropdowns (Weather removed, Lights added)
        data_schema = vol.Schema({
            vol.Required("alarm_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="alarm_control_panel")
            ),
            vol.Optional("door_sensors", default=[]): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
            ),
            vol.Optional("lights", default=[]): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["light", "switch"], multiple=True)
            ),
        })

        return self.async_show_form(
            step_id="entities", 
            data_schema=data_schema
        )


class LackeyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options reconfiguration for Lackey Hub."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the configuration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Grab current values from combined data/options to serve as defaults
        current_alarm = self.config_entry.options.get(
            "alarm_entity", self.config_entry.data.get("alarm_entity", "")
        )
        current_doors = self.config_entry.options.get(
            "door_sensors", self.config_entry.data.get("door_sensors", [])
        )
        current_lights = self.config_entry.options.get(
            "lights", self.config_entry.data.get("lights", [])
        )

        options_schema = vol.Schema({
            vol.Required("alarm_entity", default=current_alarm): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="alarm_control_panel")
            ),
            vol.Optional("door_sensors", default=current_doors): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
            ),
            vol.Optional("lights", default=current_lights): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["light", "switch"], multiple=True)
            ),
        })

        return self.async_show_form(step_id="init", data_schema=options_schema)
