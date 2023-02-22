from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback

from .manifest import manifest

class SimpleConfigFlow(ConfigFlow, domain=manifest.domain):

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        
        states = self.hass.states.async_all('calendar')
        calendars = list(map(lambda x: x.entity_id, states))

        DATA_SCHEMA = vol.Schema({
            vol.Required("calendar_id"): vol.In(calendars)
        })
        # 检测是否配置语音小助手
        if self.hass.data.get('conversation_voice') is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors = {
                'base': 'conversation'
            })

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        return self.async_create_entry(title=manifest.name, data=user_input)