"""Config flow for Qingping IoT Cloud integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant, callback

from qingping_iot_cloud import QingpingCloud
from qingping_iot_cloud.QingpingCloud import APIAuthError, APIConnectionError

from .const import DOMAIN, MIN_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
DEFAULT_TITLE = "Qingping IoT Cloud"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    cloud = QingpingCloud(data[CONF_CLIENT_ID], data[CONF_CLIENT_SECRET])
    try:
        await hass.async_add_executor_job(cloud.connect)
    except APIAuthError as err:
        raise APIAuthError from err
    except APIConnectionError as err:
        raise APIConnectionError from err
    return {"title": DEFAULT_TITLE}


class QingpingIoTCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Qingping IoT Cloud Integration."""

    VERSION = 1
    _input_data: dict[str, Any]

    @staticmethod
    @callback
    def async_get_options_flow(_: Any) -> OptionsFlow:
        """Get the options flow for this handler."""
        return QingpingIoTCloudOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except APIConnectionError:
                errors["base"] = "cannot_connect"
            except APIAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                await self.async_set_unique_id(user_input[CONF_CLIENT_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add reconfigure step to allow to reconfigure a config entry."""
        errors: dict[str, str] = {}
        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if user_input is not None:
            try:
                user_input[CONF_CLIENT_ID] = config_entry.data[CONF_CLIENT_ID]
                user_input[CONF_CLIENT_SECRET] = config_entry.data[CONF_CLIENT_SECRET]
                await validate_input(self.hass, user_input)
            except APIConnectionError:
                errors["base"] = "cannot_connect"
            except APIAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    config_entry,
                    unique_id=config_entry.unique_id,
                    data={**config_entry.data, **user_input},
                    reason="reconfigure_successful",
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CLIENT_ID, default=config_entry.data[CONF_CLIENT_ID]
                    ): str,
                    vol.Required(
                        CONF_CLIENT_SECRET,
                        default=config_entry.data[CONF_CLIENT_SECRET]
                    ): str,
                }
            ),
            errors=errors,
        )

OPTIONS_SCHEMA=vol.Schema(
    {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                ): (vol.All(vol.Coerce(int), vol.Clamp(min=MIN_SCAN_INTERVAL))),
    }
)

class QingpingIoTCloudOptionsFlowHandler(OptionsFlow):
    """Handles the options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)


        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
