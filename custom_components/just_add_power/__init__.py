"""The Just Add Power integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JAPDevice, JAPApiError
from .const import (
    DOMAIN,
    CONF_DECODERS,
    CONF_ENCODERS,
    CONF_DECODER_NAME,
    CONF_DECODER_HOST,
    CONF_ENCODER_NAME,
    CONF_ENCODER_CHANNEL,
)
from .coordinator import JAPDecoderCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]

SERVICE_SWITCH_ALL = "switch_all_decoders"
SERVICE_SWITCH_ALL_SCHEMA = vol.Schema(
    {
        vol.Required("source"): str,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Just Add Power from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    coordinators: dict[str, JAPDecoderCoordinator] = {}

    for decoder_conf in entry.data.get(CONF_DECODERS, []):
        dec_name = decoder_conf[CONF_DECODER_NAME]
        dec_host = decoder_conf[CONF_DECODER_HOST]

        device = JAPDevice(host=dec_host, session=session, name=dec_name)
        coordinator = JAPDecoderCoordinator(hass, device, dec_name)
        await coordinator.async_config_entry_first_refresh()
        coordinators[dec_host] = coordinator

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinators": coordinators,
    }

    # Build source map for services
    source_map: dict[str, int] = {}
    for enc in entry.data.get(CONF_ENCODERS, []):
        source_map[enc[CONF_ENCODER_NAME]] = enc[CONF_ENCODER_CHANNEL]

    async def handle_switch_all(call: ServiceCall) -> None:
        """Switch all decoders to the same source."""
        source = call.data["source"]
        channel = source_map.get(source)
        if channel is None:
            _LOGGER.error("Unknown source: %s", source)
            return

        for coordinator in coordinators.values():
            try:
                await coordinator.device.set_channel(channel)
                coordinator.data["channel"] = channel
            except JAPApiError as err:
                _LOGGER.error(
                    "Failed to switch %s: %s",
                    coordinator.device.host,
                    err,
                )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SWITCH_ALL,
        handle_switch_all,
        schema=SERVICE_SWITCH_ALL_SCHEMA,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
