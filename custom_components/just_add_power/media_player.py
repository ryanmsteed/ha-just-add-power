"""Media player platform for Just Add Power decoders."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
from .api import JAPApiError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up JAP media players from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinators: dict[str, JAPDecoderCoordinator] = data["coordinators"]
    encoders: list[dict[str, Any]] = entry.data.get(CONF_ENCODERS, [])

    # Build source map: friendly name -> channel number
    source_map: dict[str, int] = {}
    for enc in encoders:
        source_map[enc[CONF_ENCODER_NAME]] = enc[CONF_ENCODER_CHANNEL]

    # Build reverse map: channel number -> friendly name
    channel_to_source: dict[int, str] = {v: k for k, v in source_map.items()}

    entities = []
    for decoder_conf in entry.data.get(CONF_DECODERS, []):
        dec_name = decoder_conf[CONF_DECODER_NAME]
        dec_host = decoder_conf[CONF_DECODER_HOST]
        coordinator = coordinators[dec_host]

        entities.append(
            JAPMediaPlayer(
                coordinator=coordinator,
                name=dec_name,
                host=dec_host,
                source_map=source_map,
                channel_to_source=channel_to_source,
                entry_id=entry.entry_id,
            )
        )

    async_add_entities(entities)


class JAPMediaPlayer(CoordinatorEntity[JAPDecoderCoordinator], MediaPlayerEntity):
    """Representation of a Just Add Power decoder as a media player."""

    _attr_has_entity_name = True
    _attr_supported_features = MediaPlayerEntityFeature.SELECT_SOURCE

    def __init__(
        self,
        coordinator: JAPDecoderCoordinator,
        name: str,
        host: str,
        source_map: dict[str, int],
        channel_to_source: dict[int, str],
        entry_id: str,
    ) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"jap_{host.replace('.', '_')}"
        self._host = host
        self._source_map = source_map
        self._channel_to_source = channel_to_source
        self._attr_source_list = list(source_map.keys())
        self._attr_device_info = {
            "identifiers": {(DOMAIN, host)},
            "name": f"JAP Decoder - {name}",
            "manufacturer": "Just Add Power",
            "model": "MaxColor MC-RX2",
        }

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the player."""
        if not self.coordinator.data.get("available", False):
            return MediaPlayerState.OFF
        if self.coordinator.data.get("channel") is not None:
            return MediaPlayerState.ON
        return MediaPlayerState.IDLE

    @property
    def source(self) -> str | None:
        """Return the current source (encoder name) based on multicast channel."""
        channel = self.coordinator.data.get("channel")
        if channel is not None:
            return self._channel_to_source.get(channel)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "multicast_address": self.coordinator.data.get("multicast"),
            "channel": self.coordinator.data.get("channel"),
            "device_ip": self._host,
            "switching_mode": self.coordinator.data.get("mode"),
        }

    async def async_select_source(self, source: str) -> None:
        """Switch the decoder to a different encoder channel."""
        channel = self._source_map.get(source)
        if channel is None:
            _LOGGER.error("Unknown source: %s", source)
            return

        try:
            success = await self.coordinator.device.set_channel(channel)
            if success:
                # Optimistically update local state
                self.coordinator.data["channel"] = channel
                # Derive the new multicast address
                high = channel // 256
                low = channel % 256
                self.coordinator.data[
                    "multicast"
                ] = f"239.92.{high:02d}.{low:02d}"
                self.async_write_ha_state()
            # Refresh from device to confirm
            await self.coordinator.async_request_refresh()
        except JAPApiError as err:
            _LOGGER.error(
                "Failed to switch %s to source %s: %s",
                self._attr_name,
                source,
                err,
            )
