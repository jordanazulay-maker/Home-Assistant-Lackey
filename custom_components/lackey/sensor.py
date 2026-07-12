from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Lackey Hub sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Create a sensor for each feature flag our API returns
    features = ["alarm", "weather", "cameras"]
    sensors = [LackeyFeatureSensor(coordinator, feature, entry) for feature in features]
        
    async_add_entities(sensors)

class LackeyFeatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Lackey Hub Feature."""

    def __init__(self, coordinator, feature_name, entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._feature_name = feature_name
        self._attr_unique_id = f"{entry.entry_id}_{feature_name}"
        self._attr_name = f"Lackey {feature_name.capitalize()} Feature"
        self._attr_icon = "mdi:toggle-switch"
        
        # Visually link this sensor to the Hub device we created
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["host"])},
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        state = self.coordinator.data.get(self._feature_name)
        return "Enabled" if state else "Disabled"
