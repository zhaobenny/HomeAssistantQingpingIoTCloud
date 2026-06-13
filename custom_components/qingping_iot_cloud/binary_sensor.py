"""Binary sensors for Qingping IoT Cloud."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from qingping_iot_cloud import QingpingDevice

from .const import DOMAIN
from .coordinator import QingpingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator: QingpingCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    async_add_entities(
        QingpingOnlineBinarySensor(coordinator, device)
        for device in coordinator.data.devices
    )


class QingpingOnlineBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Connectivity sensor for a Qingping device."""

    def __init__(
        self,
        coordinator: QingpingCoordinator,
        device: QingpingDevice,
    ) -> None:
        """Initialise binary sensor."""
        super().__init__(coordinator)
        self.device = device
        self.device_mac = device.mac
        self.device_mac_formatted = (
            ":".join(self.device_mac[i:i+2] for i in range(0, len(self.device_mac), 2))
        ).upper()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        self.device = self.coordinator.get_device_by_mac(self.device_mac)
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the binary sensor is available."""
        return self.coordinator.last_update_success and self.device is not None

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return device class."""
        return BinarySensorDeviceClass.CONNECTIVITY

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            name=f"{self.device.name}",
            manufacturer="Qingping",
            model=self.device.product_en_name,
            sw_version=self.device.version,
            identifiers={
                (
                    DOMAIN,
                    f"{self.coordinator.data.controller_name}-{self.device.mac}",
                )
            },
            connections={("mac", self.device_mac_formatted)},
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the device is online."""
        if not self.available:
            return None
        return not self.device.status_offline

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"{self.device.name} Online"

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{DOMAIN}-{self.device_mac}-online"
