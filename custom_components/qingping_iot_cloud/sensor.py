"""Interfaces with the Integration 101 Template api sensors."""

import datetime
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from qingping_iot_cloud import QingpingDevice

from .const import DOMAIN, MAX_DELAY_MULTIPLIER
from .coordinator import QingpingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sensors."""
    coordinator: QingpingCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    sensors = []
    sensors.extend(
        QingpingSensor(coordinator, device, attribute)
        for device in coordinator.data.devices
        for attribute in device.data
    )
    async_add_entities(sensors)


class QingpingSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a sensor."""

    def __init__(
        self, coordinator: QingpingCoordinator, device: QingpingDevice, attribute: str
    ) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self.device = device
        self.device_mac = device.mac
        self.device_mac_formatted = (
            ":".join(self.device_mac[i:i+2] for i in range(0, len(self.device_mac), 2))
        ).upper()
        self.attribute = attribute
        self._parse_values()

    def _parse_values(self) -> None:
        self._raw_value = self.device.get_property(self.attribute).get_ha_value()
        self._is_missing = self._raw_value is None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        self.device = self.coordinator.get_device_by_mac(
            self.device_mac
        )
        self._parse_values()
        self.async_write_ha_state()

    @property
    def device_class(self) -> str:
        """Return device class."""
        ha_class = self.device.get_property(self.attribute).get_ha_class()
        if ha_class is None:
            return None
        return SensorDeviceClass(ha_class)

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
        """Return the name of the sensor."""
        ha_title = self.device.get_property(self.attribute).get_ha_title()
        return f"{self.device.name} {ha_title}"


    def _seconds_since_last_update(self) -> int:
        device_last_timestamp = int(self.device.get_property("timestamp").value)
        now = int(datetime.datetime.timestamp(datetime.datetime.now(datetime.UTC)))
        return now - device_last_timestamp

    @property
    def available(self) -> bool:
        """Return True if the sensor is available."""
        if self.attribute == "timestamp": # timestamp should always be reported
            return True
        # last_update_success is False when UpdateFailed is raised
        if self.coordinator.last_update_success:
            if self._is_missing:
                return False
            delta = self._seconds_since_last_update()
            max_delay = MAX_DELAY_MULTIPLIER*self.device.setting_report_interval
            if delta > max_delay:
                message = (
                    f"Device {self.device_mac} is offline for {delta} seconds, which is"
                    f" more than MAX_DELAY_MULTIPLIER({MAX_DELAY_MULTIPLIER}) * "
                    f"setting_report_interval({self.device.setting_report_interval})"
                )
                _LOGGER.info(message)
                return False
            return True
        return False

    @property
    def native_value(self) -> int | float:
        """Return the state of the entity."""
        return STATE_UNAVAILABLE if not self.available else self._raw_value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return unit of temperature."""
        return self.device.get_property(self.attribute).get_unit()

    @property
    def state_class(self) -> str | None:
        """Return state class."""
        # https://developers.home-assistant.io/docs/core/entity/sensor/#available-state-classes
        if self.attribute == "timestamp":
            return None
        return SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return f"{DOMAIN}-{self.device_mac}-{self.attribute}"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the extra state attributes."""
        attrs = {}
        attrs["timestamp"] = self.device.get_property("timestamp").value
        attrs["nickname"] = self.device.name
        attrs["offline"] = self.device.status_offline
        attrs["setting_report_interval"] = self.device.setting_report_interval
        attrs["setting_collect_interval"] = self.device.setting_collect_interval
        return attrs
