"""Number entities for Qingping IoT Cloud device settings."""

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from qingping_iot_cloud import QingpingDevice

from .const import (
    DOMAIN,
    MIN_COLLECT_INTERVAL,
    MIN_REPORT_INTERVAL,
)
from .coordinator import QingpingCoordinator


@dataclass(frozen=True)
class QingpingIntervalEntityDescription:
    """Description for Qingping interval setting entities."""

    key: str
    name: str
    device_attr: str
    native_min_value: int


INTERVAL_DESCRIPTIONS = (
    QingpingIntervalEntityDescription(
        key="report_interval",
        name="Report Interval",
        device_attr="setting_report_interval",
        native_min_value=MIN_REPORT_INTERVAL,
    ),
    QingpingIntervalEntityDescription(
        key="collect_interval",
        name="Collect Interval",
        device_attr="setting_collect_interval",
        native_min_value=MIN_COLLECT_INTERVAL,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number entities."""
    coordinator: QingpingCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    async_add_entities(
        QingpingIntervalNumber(coordinator, device, description)
        for device in coordinator.data.devices
        for description in INTERVAL_DESCRIPTIONS
    )


class QingpingIntervalNumber(CoordinatorEntity, NumberEntity):
    """Number entity for a Qingping device interval setting."""

    _attr_mode = NumberMode.BOX
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(
        self,
        coordinator: QingpingCoordinator,
        device: QingpingDevice,
        description: QingpingIntervalEntityDescription,
    ) -> None:
        """Initialise number entity."""
        super().__init__(coordinator)
        self.device = device
        self.device_mac = device.mac
        self.device_mac_formatted = (
            ":".join(self.device_mac[i:i+2] for i in range(0, len(self.device_mac), 2))
        ).upper()
        self.interval_description = description

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update entity with latest data from coordinator."""
        self.device = self.coordinator.get_device_by_mac(self.device_mac)
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the number entity is available."""
        return self.coordinator.last_update_success and self.device is not None

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
    def name(self) -> str:
        """Return the name of the number entity."""
        return f"{self.device.name} {self.interval_description.name}"

    @property
    def native_min_value(self) -> int:
        """Return the minimum interval setting."""
        return self.interval_description.native_min_value

    @property
    def native_value(self) -> int | None:
        """Return the current interval setting."""
        if not self.available:
            return None
        return getattr(self.device, self.interval_description.device_attr)

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{DOMAIN}-{self.device_mac}-{self.interval_description.key}"

    async def async_set_native_value(self, value: float) -> None:
        """Update the interval setting."""
        if self.device is None:
            msg = "Device is not available"
            raise HomeAssistantError(msg)

        new_value = int(value)
        if new_value < self.interval_description.native_min_value:
            msg = (
                f"{self.interval_description.name} must be at least "
                f"{self.interval_description.native_min_value} seconds"
            )
            raise HomeAssistantError(msg)

        report_interval = self.device.setting_report_interval
        collect_interval = self.device.setting_collect_interval

        if self.interval_description.key == "report_interval":
            report_interval = new_value
        else:
            collect_interval = new_value

        if report_interval % collect_interval != 0:
            msg = "Report interval must be an integer multiple of collect interval"
            raise HomeAssistantError(msg)

        await self.coordinator.async_update_device_settings(
            self.device_mac,
            report_interval,
            collect_interval,
        )
