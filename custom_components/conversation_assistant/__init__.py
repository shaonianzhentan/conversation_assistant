from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
import re, urllib

import logging, json, datetime, uuid

from recognizers_suite import recognize_datetime, Culture, ModelResult

from .manifest import manifest

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.deprecated(manifest.domain)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault('conversation_assistant', ConversationAssistant(hass, entry.options))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    del hass.data['conversation_assistant']
    return True

class ConversationAssistant:

    def __init__(self, hass, config) -> None:
        self.hass = hass
        self.calendar_id = config.get('calendar_id')
        self.music_id = config.get('music_id')
        self.weather_id = config.get('weather_id')
        pass

    async def async_process(self, text):
        result = await self.async_calendar(text)
        if result is not None:
            return result

    async def async_calendar(self, text):
        if '提醒我' in text:
            arr = text.split('提醒我')
            time_text = arr[0]
            # 判断是否输入时间
            if time_text.count(':') == 1:
                time_text = time_text.replace(':', '点')
            description = arr[1]
            results = recognize_datetime(time_text, Culture.Chinese)
            length = len(results)
            if length > 0:
                result = results[length - 1]
                values = list(result.resolution.values())[0]
                value = values[len(values) - 1]

                t = value['type']
                v = value['value']

                start_date_time = None
                now = datetime.datetime.now()

                if t == 'datetime':
                    start_date_time = v
                elif t == 'time':
                    localtime = now.strftime('%Y-%m-%d %H:%M:%S')
                    if v < localtime[11:]:
                        return '时间已经过去了'
                    start_date_time = localtime[:11] + v
                elif t == 'duration':
                    now = now + datetime.timedelta(seconds=+int(v))
                    start_date_time = now.strftime('%Y-%m-%d %H:%M:%S')

                if start_date_time is not None:
                    # 结束时间
                    end_date_time = datetime.datetime.strptime(start_date_time, '%Y-%m-%d %H:%M:%S')
                    end_date_time = end_date_time + datetime.timedelta(seconds=+60)

                    await self.hass.services.async_call('calendar', 'create_event', {
                        'entity_id': self.calendar_id,
                        'start_date_time': start_date_time,
                        'end_date_time': end_date_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'summary': description,
                        'description': text
                    })
                    return f'【{start_date_time}】{description}'