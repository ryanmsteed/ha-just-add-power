"""API client for Just Add Power devices."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
API_SETTINGS = "/cgi-bin/api/settings"
API_CHANNEL = "/cgi-bin/api/command/channel"


class JAPApiError(Exception):
    """Exception for JAP API errors."""


class JAPDevice:
    """Represents a Just Add Power encoder or decoder."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        name: str | None = None,
    ) -> None:
        """Initialize the JAP device."""
        self.host = host
        self.name = name
        self._session = session
        self._base_url = f"http://{host}"

    async def get_settings(self) -> dict[str, Any]:
        """Get all settings from the device."""
        url = f"{self._base_url}{API_SETTINGS}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(url) as resp:
                    resp.raise_for_status()
                    result = await resp.json(content_type=None)
                    return result.get("data", {})
        except asyncio.TimeoutError as err:
            raise JAPApiError(
                f"Timeout communicating with {self.host}"
            ) from err
        except aiohttp.ClientError as err:
            raise JAPApiError(
                f"Error communicating with {self.host}: {err}"
            ) from err
        except Exception as err:
            raise JAPApiError(
                f"Unexpected error communicating with {self.host}: {err}"
            ) from err

    async def set_channel(self, channel: int) -> bool:
        """Set the channel on a decoder (switch source).

        The JAP API expects a plain text body with just the channel number.
        """
        url = f"{self._base_url}{API_CHANNEL}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.post(
                    url, data=str(channel)
                ) as resp:
                    resp.raise_for_status()
                    result = await resp.json(content_type=None)
                    return result.get("data") == "OK"
        except asyncio.TimeoutError as err:
            raise JAPApiError(
                f"Timeout communicating with {self.host}"
            ) from err
        except aiohttp.ClientError as err:
            raise JAPApiError(
                f"Error communicating with {self.host}: {err}"
            ) from err
        except Exception as err:
            raise JAPApiError(
                f"Unexpected error communicating with {self.host}: {err}"
            ) from err

    async def get_current_channel(self) -> int | None:
        """Get the current channel by parsing the multicast address from settings.

        Multicast address format: 239.92.XX.YY
        Channel = (XX * 256) + YY
        e.g., 239.92.00.01 = channel 1, 239.92.00.02 = channel 2
        """
        try:
            settings = await self.get_settings()
            multicast = (
                settings.get("device", {}).get("network", {}).get("multicast")
            )
            if not multicast:
                return None
            parts = multicast.split(".")
            if len(parts) != 4:
                return None
            return (int(parts[2]) * 256) + int(parts[3])
        except (JAPApiError, ValueError, IndexError):
            return None

    async def get_device_info(self) -> dict[str, Any]:
        """Get device information from settings."""
        try:
            settings = await self.get_settings()
            device = settings.get("device", {})
            network = device.get("network", {})
            return {
                "name": device.get("name"),
                "id": device.get("id"),
                "ip": network.get("ipaddress"),
                "multicast": network.get("multicast"),
                "mode": settings.get("system", {}).get("mode"),
            }
        except JAPApiError:
            return {}

    async def test_connection(self) -> bool:
        """Test if the device is reachable."""
        try:
            await self.get_settings()
            return True
        except JAPApiError:
            return False
