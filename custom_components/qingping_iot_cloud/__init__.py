"""The Qingping IoT Cloud integration."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass

from aiohttp.web import Request
from homeassistant.components.cloud import async_get_or_create_cloudhook
from homeassistant.components.persistent_notification import (
    create as persistent_notification_create,
)
from homeassistant.components.webhook import (
    async_generate_url,
    async_register,
    async_unregister,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from qingping_iot_cloud import QingpingDeviceProperty

from .const import DOMAIN
from .coordinator import QingpingCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
]


@dataclass
class RuntimeData:
    """Class to hold your data."""

    coordinator: DataUpdateCoordinator
    cancel_update_listener: Callable


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Qingping IoT Cloud Integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = QingpingCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.cloud.is_connected():
        raise ConfigEntryNotReady

    cancel_update_listener = config_entry.add_update_listener(_async_update_listener)

    hass.data[DOMAIN][config_entry.entry_id] = RuntimeData(
        coordinator, cancel_update_listener
    )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    if config_entry.entry_id not in hass.data.get("webhook", {}):
        async_register(
            hass,
            DOMAIN,
            f"{DOMAIN} - {config_entry.entry_id}",
            config_entry.entry_id,
            handle_webhook
        )
        _LOGGER.info(
            "Registered webhook %s for config entry %s",
            config_entry.entry_id,
            config_entry.entry_id
        )
    else:
        _LOGGER.info("webhook %s already registered", config_entry.entry_id)

    webhook_url = async_generate_url(hass, config_entry.entry_id)
    with contextlib.suppress(Exception):
        webhook_url = await async_get_or_create_cloudhook(hass, config_entry.entry_id)

    persistent_notification_create(
        hass,
        (
            f"Your webhook public URL is: {webhook_url}\n\n"
            "Go to https://developer.qingping.co/personal/dataPushSetting"
            "and provide the above URL."
        ), # TODO: handle local only URL
        title="Qingping IoT Cloud - ability to use incoming Webhooks",
        notification_id="qingping_notification"
    )


    return True


async def _async_update_listener(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Handle config options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry  # noqa: ARG001
) -> bool:
    """Delete device if selected from UI."""
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN][config_entry.entry_id].cancel_update_listener()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    async_unregister(hass, config_entry.entry_id)

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok

@callback
async def handle_webhook(
    hass: HomeAssistant, webhook_id: str, request: Request
) -> None:
    """Handle incoming webhook data."""
    try:
        incoming_data = await request.json()
        diagnose_data = f"{webhook_id} received webhook payload: {incoming_data}"
        _LOGGER.debug(diagnose_data)

        mac = incoming_data["payload"]["info"]["mac"] # required for data to be valid
        coordinator = hass.data[DOMAIN][webhook_id].coordinator
        new_data = coordinator.get_device_by_mac(mac).data

        # TODO: can `data` be longer than 1 element?
        data_len = len(incoming_data["payload"]["data"])
        if data_len != 1:
            msg = (
                f"WEBHOOK_PAYLOAD_DATA_LEN webhook {webhook_id} received payload with "
                f"{data_len} elements in data, expected 1"
            )
            _LOGGER.warning(msg)
        for property_name, property_data in incoming_data["payload"]["data"][0].items():
          new_data[property_name] = QingpingDeviceProperty.QingpingDeviceProperty(
            property=property_name,
            value=property_data.get("value", None),
            status=property_data.get("status", 0)
          )
        coordinator.get_device_by_mac(mac).data = new_data
        hass.data[DOMAIN][webhook_id].coordinator.async_set_updated_data(coordinator.data)
    except Exception:
        diagnose_data = (
            f"{webhook_id} received webhook payload that's not valid: "
            f"{await request.text()}"
        )
        _LOGGER.warning(diagnose_data)
        raise
