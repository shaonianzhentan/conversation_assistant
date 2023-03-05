from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
import re, urllib

import logging, json, datetime, uuid

from recognizers_suite import recognize_datetime, Culture, ModelResult

from .manifest import manifest

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.deprecated(manifest.domain)

DOMAIN = manifest.domain

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ''' 安装集成 '''
    await update_listener(hass, entry)

    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def update_listener(hass, entry):
    ''' 更新配置 '''
    if hass.data.get(DOMAIN) is not None:
        del hass.data[DOMAIN]
    hass.data.setdefault(DOMAIN, ConversationAssistant(hass, entry.options))

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ''' 删除集成 '''
    del hass.data[DOMAIN]
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

        result = await self.async_music(text)
        if result is not None:
            return result

    async def async_music(self, text):
        if self.music_id is not None:
            service_name = None
            service_data = {
                'entity_id': self.music_id
            }
            if text == '播放':
                service_name= 'media_play'
            elif text == '暂停':
                service_name= 'media_pause'
            elif text == '上一曲':
                service_name= 'media_previous_track'
            elif text == '下一曲':
                service_name= 'media_next_track'
            elif ['声音小点', '小点声音', '小一点声音', '声音小一点'].count(text) == 1:
                service_name= 'volume_down'
            elif ['声音大点', '大点声音', '大一点声音', '声音大一点'].count(text) == 1:
                service_name= 'volume_up'
            elif text.startswith('我想听'):
                arr = text.split('我想听')
                if len(arr) == 2 and arr[1] != '':
                    kv = arr[1]
                    media_id = f'cloudmusic://search/play?kv={kv}'

                    if ['每日推荐', '每日推荐音乐', '每日推荐歌曲', '每日推荐歌单'].count(kv) == 1:
                        media_id = 'cloudmusic://163/my/daily'
                    elif kv.endswith('歌单'):
                        media_id = f'cloudmusic://play/list?kv={kv}'

                    service_name = 'play_media'
                    service_data.update({
                        'media_content_type': 'music',
                        'media_content_id': media_id
                    })
                    text = '正在搜索匹配中'
            elif text.startswith('播放电台'):
                pass
            elif text.startswith('播放歌单'):
                pass
            elif text.startswith('播放专辑'):
                pass

            if service_name is not None:
                await self.hass.services.async_call('media_player', service_name, service_data)
                return f'音乐{text}'

    async def async_calendar(self, text):
        if self.calendar_id is not None and '提醒我' in text:
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
                print(values)
                value = values[0]
                t = value['type']
                v = value['value']

                now = datetime.datetime.now()
                start_date_time = None

                # 早晚
                if len(values) == 2:
                    # 和当前时间比较
                    if t == 'time':
                        if now.strftime('%H:%M:%S') > v:
                            value = values[1]
                            t = value['type']
                            v = value['value']

                if t == 'datetime':
                    start_date_time = v
                elif t == 'time':
                    localtime = now.strftime('%Y-%m-%d %H:%M:%S')
                    if v < localtime[11:]:
                        return '时间已经过去了，没有提醒的必要啦'
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