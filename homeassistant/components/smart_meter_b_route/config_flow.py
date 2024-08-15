"""Config flow for Smart Meter B Route integration."""

import logging
from typing import Any

from momonga import Momonga, MomongaSkJoinFailure, MomongaSkScanFailure
from serial import Serial
from serial.tools.list_ports import comports
import voluptuous as vol

from homeassistant.components.usb import (
    UsbServiceInfo,
    get_serial_by_id,
    human_readable_device_name,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_DEVICE, CONF_ID, CONF_PASSWORD
from homeassistant.core import callback

from .const import DOMAIN, ENTRY_TITLE

_LOGGER = logging.getLogger(__name__)


def activate_ascii_mode_if_needed(device: str) -> None:
    """Activate ASCII mode if needed."""
    serial = Serial(device, 115200)
    serial.write(b"ROPT\r")
    _LOGGER.debug(serial.readline())
    mode = serial.read_until(b"\r").strip()
    _LOGGER.info("Mode: %s", mode)
    if mode == b"OK 00":
        _LOGGER.info("Activating ASCII mode")
        serial.write(b"WOPT 01\r")
    else:
        _LOGGER.info("ASCII mode already active")
    serial.flush()
    serial.close()


def validate_input(device: str, id: str, password: str) -> None:
    """Validate the user input allows us to connect."""
    activate_ascii_mode_if_needed(device)
    with Momonga(dev=device, rbid=id, pwd=password):
        pass


class BRouteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Meter B Route."""

    VERSION = 1

    @callback
    async def get_usb_devices(self) -> dict[str, str]:
        """Return a list of available USB devices."""
        devices = await self.hass.async_add_executor_job(comports)
        return {
            get_serial_by_id(port.device): human_readable_device_name(
                port.device,
                port.serial_number,
                port.manufacturer,
                port.description,
                port.vid,
                port.pid,
            )
            for port in devices
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if (
            user_input is not None
            and CONF_ID in user_input
            and CONF_PASSWORD in user_input
        ):
            try:
                await self.hass.async_add_executor_job(
                    validate_input,
                    user_input[CONF_DEVICE],
                    user_input[CONF_ID],
                    user_input[CONF_PASSWORD],
                )
            except MomongaSkScanFailure:
                errors["base"] = "cannot_connect"
            except MomongaSkJoinFailure:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    user_input[CONF_ID], raise_on_progress=False
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=ENTRY_TITLE, data=user_input)

        device_options = await self.get_usb_devices()
        first_device = list(device_options.keys())[0]
        default_device: str = (
            user_input.get(CONF_DEVICE, first_device) if user_input else first_device
        )
        data_schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE, default=default_device): vol.In(
                    device_options
                ),
                vol.Required(CONF_ID): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_usb(self, discovery_info: UsbServiceInfo) -> ConfigFlowResult:
        """Handle a step triggered by USB device detection."""
        device = discovery_info.device
        user_input = {
            CONF_DEVICE: device,
        }
        return await self.async_step_user(user_input)
