"""DataUpdateCoordinator for Just Add Power decoders."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import JAPDevice, JAPApiError
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class JAPDecoderCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to poll a single JAP decoder for its current state."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: JAPDevice,
        name: str,
    ) -> None:
        """Initialize the coordinator."""
        self.device = device
        super().__init__(
            hass,
            _LOGGER,
            name=f"JAP {name}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch current state from the decoder."""
        try:
            settings = await self.device.get_settings()
            device_info = settings.get("device", {})
            network = device_info.get("network", {})
            multicast = network.get("multicast", "")

            # Parse channel from multicast address (239.92.XX.YY)
            channel = None
            if multicast:
                try:
                    parts = multicast.split(".")
                    if len(parts) == 4:
                        channel = (int(parts[2]) * 256) + int(parts[3])
                except (ValueError, IndexError):
                    pass

            return {
                "channel": channel,
                "available": True,
                "name": device_info.get("name"),
                "multicast": multicast,
                "ip": network.get("ipaddress"),
                "mode": settings.get("system", {}).get("mode"),
            }
        except JAPApiError as err:
            _LOGGER.debug(
                "Error fetching data from %s: %s", self.device.host, err
            )
            return {
                "channel": None,
                "available": False,
                "name": None,
                "multicast": None,
                "ip": None,
                "mode": None,
            }
