"""Qingping IoT Cloud integration using DataUpdateCoordinator."""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import timedelta

import requests
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from qingping_iot_cloud import QingpingCloud, QingpingDevice
from qingping_iot_cloud.QingpingCloud import APIAuthError, APIConnectionError

from .const import DEFAULT_SCAN_INTERVAL, HTTP_GET_TIMEOUT

_LOGGER = logging.getLogger(__name__)


@dataclass
class QingpingAPIData:
    """Class to hold api data."""

    controller_name: str
    devices: list[QingpingDevice.QingpingDevice]


class QingpingCoordinator(DataUpdateCoordinator):
    """My Qingping coordinator."""

    data: QingpingAPIData

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.app_key = config_entry.data[CONF_CLIENT_ID]
        self.app_secret = config_entry.data[CONF_CLIENT_SECRET]

        self.poll_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=self.poll_interval),
        )

        self.cloud = QingpingCloud(app_key=self.app_key, app_secret=self.app_secret)

    async def async_update_data(self) -> QingpingAPIData:
        """
        Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        _LOGGER.debug("Starting QingpingCoordinator.async_update_data")
        try:
            await asyncio.wait_for(
                self.hass.async_add_executor_job(self.cloud.connect),
                HTTP_GET_TIMEOUT
            )
            devices = await asyncio.wait_for(
                self.hass.async_add_executor_job(self.cloud.get_devices),
                HTTP_GET_TIMEOUT
            )
        except Exception as err:
            error_message = f"Error communicating with API: {err}"
            _LOGGER.error(error_message) # noqa: TRY400 # this is reallynot exception, rather some expected error
            raise UpdateFailed(error_message) from err

        return QingpingAPIData(self.cloud.API_URL_PREFIX, devices)

    async def async_update_device_settings(
        self,
        mac: str,
        report_interval: int,
        collect_interval: int,
    ) -> None:
        """Update data report settings for a Qingping device."""
        await asyncio.wait_for(
            self.hass.async_add_executor_job(
                self._update_device_settings,
                mac,
                report_interval,
                collect_interval,
            ),
            HTTP_GET_TIMEOUT,
        )
        await self.async_request_refresh()

    def _update_device_settings(
        self,
        mac: str,
        report_interval: int,
        collect_interval: int,
    ) -> None:
        """Call Qingping settings API."""
        self.cloud.connect()
        url = f"{self.cloud.API_URL_PREFIX}/devices/settings"
        payload = {
            "mac": [mac],
            "report_interval": report_interval,
            "collect_interval": collect_interval,
            "timestamp": int(time.time() * 1000),
        }
        response = requests.put(
            url,
            auth=self.cloud._auth,  # noqa: SLF001
            json=payload,
            timeout=HTTP_GET_TIMEOUT,
        )
        _LOGGER.debug("API PUT %s RESPONSE CODE: %s", url, response.status_code)
        if response.ok:
            return

        _LOGGER.debug("API PUT %s RESPONSE BODY: %s", url, response.text)
        msg = f"Error updating device settings: {response.status_code}"
        if response.status_code in (401, 403):
            raise APIAuthError(msg)
        raise APIConnectionError(msg)

    def get_device_by_mac(
        self, device_mac: int
    ) -> QingpingDevice.QingpingDevice | None:
        """Return device by device MAC."""
        try:
            return next(
                (device for device in self.data.devices if device.mac == device_mac),
                None
            )
        except IndexError:
            return None
