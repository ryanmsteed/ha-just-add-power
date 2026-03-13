"""Config flow for Just Add Power integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JAPDevice
from .const import (
    DOMAIN,
    CONF_DECODERS,
    CONF_ENCODERS,
    CONF_DECODER_NAME,
    CONF_DECODER_HOST,
    CONF_ENCODER_NAME,
    CONF_ENCODER_CHANNEL,
)

_LOGGER = logging.getLogger(__name__)


class JAPConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Just Add Power."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._encoders: list[dict[str, Any]] = []
        self._decoders: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step - collect first encoder."""
        if user_input is not None:
            self._encoders.append(
                {
                    CONF_ENCODER_NAME: user_input[CONF_ENCODER_NAME],
                    CONF_ENCODER_CHANNEL: user_input[CONF_ENCODER_CHANNEL],
                }
            )
            return await self.async_step_encoder_menu()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENCODER_NAME): str,
                    vol.Required(CONF_ENCODER_CHANNEL): int,
                }
            ),
        )

    async def async_step_encoder_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Menu: add another encoder or proceed to decoders."""
        return self.async_show_menu(
            step_id="encoder_menu",
            menu_options=["add_encoder", "add_decoder"],
            description_placeholders={
                "count": str(len(self._encoders)),
            },
        )

    async def async_step_add_encoder(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add another encoder."""
        if user_input is not None:
            self._encoders.append(
                {
                    CONF_ENCODER_NAME: user_input[CONF_ENCODER_NAME],
                    CONF_ENCODER_CHANNEL: user_input[CONF_ENCODER_CHANNEL],
                }
            )
            return await self.async_step_encoder_menu()

        return self.async_show_form(
            step_id="add_encoder",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENCODER_NAME): str,
                    vol.Required(CONF_ENCODER_CHANNEL): int,
                }
            ),
        )

    async def async_step_add_decoder(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add a decoder."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            device = JAPDevice(user_input[CONF_DECODER_HOST], session)

            try:
                reachable = await device.test_connection()
                if not reachable:
                    errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "cannot_connect"

            if not errors:
                self._decoders.append(
                    {
                        CONF_DECODER_NAME: user_input[CONF_DECODER_NAME],
                        CONF_DECODER_HOST: user_input[CONF_DECODER_HOST],
                    }
                )
                return await self.async_step_decoder_menu()

        return self.async_show_form(
            step_id="add_decoder",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DECODER_NAME): str,
                    vol.Required(CONF_DECODER_HOST): str,
                }
            ),
            errors=errors,
        )

    async def async_step_decoder_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Menu: add another decoder or finish."""
        return self.async_show_menu(
            step_id="decoder_menu",
            menu_options=["add_another_decoder", "finish"],
            description_placeholders={
                "count": str(len(self._decoders)),
            },
        )

    async def async_step_add_another_decoder(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add another decoder - redirects to add_decoder."""
        return await self.async_step_add_decoder(user_input)

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create the config entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="Just Add Power",
            data={
                CONF_ENCODERS: self._encoders,
                CONF_DECODERS: self._decoders,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> JAPOptionsFlow:
        """Get the options flow."""
        return JAPOptionsFlow(config_entry)


class JAPOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Just Add Power."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_encoder", "add_decoder", "done"],
        )

    async def async_step_add_encoder(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add an encoder via options."""
        if user_input is not None:
            data = dict(self._config_entry.data)
            encoders = list(data.get(CONF_ENCODERS, []))
            encoders.append(
                {
                    CONF_ENCODER_NAME: user_input[CONF_ENCODER_NAME],
                    CONF_ENCODER_CHANNEL: user_input[CONF_ENCODER_CHANNEL],
                }
            )
            data[CONF_ENCODERS] = encoders
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=data
            )
            await self.hass.config_entries.async_reload(
                self._config_entry.entry_id
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_encoder",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENCODER_NAME): str,
                    vol.Required(CONF_ENCODER_CHANNEL): int,
                }
            ),
        )

    async def async_step_add_decoder(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add a decoder via options."""
        if user_input is not None:
            data = dict(self._config_entry.data)
            decoders = list(data.get(CONF_DECODERS, []))
            decoders.append(
                {
                    CONF_DECODER_NAME: user_input[CONF_DECODER_NAME],
                    CONF_DECODER_HOST: user_input[CONF_DECODER_HOST],
                }
            )
            data[CONF_DECODERS] = decoders
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=data
            )
            await self.hass.config_entries.async_reload(
                self._config_entry.entry_id
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_decoder",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DECODER_NAME): str,
                    vol.Required(CONF_DECODER_HOST): str,
                }
            ),
        )

    async def async_step_done(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Finish options."""
        return self.async_create_entry(title="", data={})
