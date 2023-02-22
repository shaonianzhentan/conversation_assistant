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
        
        DATA_SCHEMA = vol.Schema({})
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
    
    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry):
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        default_name = '停止控制'
        options = self.config_entry.options
        errors = {}
        if user_input is not None:
            if user_input.get('calendar_id') == default_name:
                del user_input['calendar_id']
            if user_input.get('weather_id') == default_name:
                del user_input['weather_id']
            if user_input.get('music_id') == default_name:
                del user_input['music_id']
            return self.async_create_entry(title='', data=user_input)

        calendar_states = self.hass.states.async_all('calendar')
        calendar_entities = list(map(lambda x: x.entity_id, calendar_states))
        calendar_entities.append(default_name)

        weather_states = self.hass.states.async_all('weather')
        weather_entities = list(map(lambda x: x.entity_id, weather_states))
        weather_entities.append(default_name)

        media_states = self.hass.states.async_all('media_player')
        media_entities = list(map(lambda x: x.entity_id, media_states))
        media_entities.append(default_name)

        DATA_SCHEMA = vol.Schema({
            vol.Optional("calendar_id", default=options.get('calendar_id', default_name)): vol.In(calendar_entities),
            vol.Optional("weather_id", default=options.get('weather_id', default_name)): vol.In(weather_entities),
            vol.Optional("music_id", default=options.get('music_id', default_name)): vol.In(media_entities)
        })
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)