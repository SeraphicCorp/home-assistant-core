"""Test the Smart Meter B-route config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock, Mock, patch

from momonga import MomongaSkJoinFailure, MomongaSkScanFailure
import pytest
from serial.tools.list_ports_linux import SysFS

from homeassistant.components.smart_meter_b_route.const import DOMAIN, ENTRY_TITLE
from homeassistant.components.usb import UsbServiceInfo
from homeassistant.config_entries import SOURCE_USB, SOURCE_USER
from homeassistant.const import CONF_DEVICE, CONF_ID, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from . import user_input


@pytest.fixture
def mock_comports() -> Generator[AsyncMock]:
    """Override comports."""
    with patch(
        "homeassistant.components.smart_meter_b_route.config_flow.comports",
        return_value=[SysFS("/dev/ttyUSB41"), SysFS("/dev/ttyUSB42")],
    ) as mock:
        yield mock


async def test_step_user_form(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_comports: AsyncMock,
    mock_momonga: Mock,
) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == ENTRY_TITLE
    assert result["data"] == user_input
    mock_setup_entry.assert_called_once()
    mock_comports.assert_called()
    mock_momonga.assert_called_once_with(
        dev=user_input[CONF_DEVICE],
        rbid=user_input[CONF_ID],
        pwd=user_input[CONF_PASSWORD],
    )


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (MomongaSkJoinFailure, "invalid_auth"),
        (MomongaSkScanFailure, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_step_user_form_errors(
    hass: HomeAssistant,
    error: Exception,
    message: str,
    mock_setup_entry: AsyncMock,
    mock_comports: AsyncMock,
    mock_momonga: AsyncMock,
) -> None:
    """Test we handle error."""
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    mock_momonga.side_effect = error
    result_configure = await hass.config_entries.flow.async_configure(
        result_init["flow_id"],
        user_input,
    )

    assert result_configure["type"] is FlowResultType.FORM
    assert result_configure["errors"] == {"base": message}
    await hass.async_block_till_done()
    mock_comports.assert_called()
    mock_momonga.assert_called_once_with(
        dev=user_input[CONF_DEVICE],
        rbid=user_input[CONF_ID],
        pwd=user_input[CONF_PASSWORD],
    )

    mock_momonga.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result_configure["flow_id"],
        user_input,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_step_usb(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_comports: AsyncMock,
    mock_momonga: Mock,
) -> None:
    """Test step usb."""
    discovery_info = UsbServiceInfo(
        device="/dev/ttyZIGBEE",
        pid="AAAA",
        vid="AAAA",
        serial_number="1234",
        description="zigbee radio",
        manufacturer="test",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USB}, data=discovery_info
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
