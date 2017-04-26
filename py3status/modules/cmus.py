# -*- coding: utf-8 -*-
"""
Display currently playing song in cmus.

cmus (C* Music Player) is a small, fast and powerful console audio player
which supports most major audio formats. Various features include gapless
playback, ReplayGain support, MP3 and Ogg streaming, live filtering, instant
startup, customizable key-bindings, and vi-style default key-bindings.

Configuration parameters:
    button_next: mouse button to skip next track (default None)
    button_pause: mouse button to pause/play the playback (default 1)
    button_previous: mouse button to skip previous track (default None)
    button_repeat: mouse button to toggle repeat (default None)
    button_seek_backward: mouse button to seek backward (default None)
    button_seek_forward: mouse button to seek forward (default None)
    button_shuffle: mouse button to toggle shuffle (default None)
    button_stop: mouse button to stop the playback (default 3)
    button_volume_down: mouse button to decrease volume (default None)
    button_volume_up: mouse button to increase volume (default None)
    cache_timeout: refresh interval for this module (default 5)
    format: display format for this module
        (default '[\?if=is_started [\?if=is_playing > ][\?if=is_paused \|\| ]
        [\?if=is_stopped .. ][[{artist}][\?soft  - ][{title}]
        |\?show cmus: waiting for user input]]')
    sleep_timeout: sleep interval for this module (default 20)

Control placeholders:
    is_paused: a boolean based on cmus status
    is_playing: a boolean based on cmus status
    is_started: a boolean based on cmus status
    is_stopped: a boolean based on cmus status
    ----------
    continue: a boolean based on data status
    follow: a boolean based on data status
    play_library: a boolean based on data status
    play_sorted: a boolean based on data status
    repeat: a boolean based on data status
    repeat_current: a boolean based on data status
    replaygain: a boolean based on data status
    replaygain_limit: a boolean based on data status
    shuffle: a boolean based on data status
    softvol: a boolean based on data status
    stream: a boolean based on data status

Format placeholders:
    {durationtime} length time in [HH:]MM:SS, eg 02:51
    {positiontime} elapsed time in [HH:]MM:SS, eg 00:17
    ----------
    {aaa_mode} shuffle songs between artist, album, or all. eg album
    {albumartist} album artist
    {album} album name
    {artist} artist name
    {bitrate} audio bitrate, eg 229
    {comment} comment, eg URL
    {date} year number, eg 2015
    {duration} length time in seconds, eg 171
    {file} file location, eg /home/user/Music...
    {position} elapsed time in seconds, eg 17
    {replaygain_preamp} replay gain preamp, eg 0.000000
    {status} playback status, eg playing, paused, or stopped
    {title} track title
    {tracknumber} track number, eg 0
    {vol_left} left volume number, eg 90
    {vol_right} right volume number, eg 90

    Placeholders are retrieved directly from `cmus-remote --query` command.
    The list was harvested only once and should not represent a full list.

Color options:
    color_paused: Paused, defaults to color_degraded
    color_playing: Playing, defaults to color_good
    color_stopped: Stopped, defaults to color_bad

Requires:
    cmus: a small feature-rich ncurses-based music player

Examples:
```
# copy right side of cmus status line (for fun)
cmus {
    format += '[\?soft  ]' +\
        '[\?is_started&color=#ccc [\?if=play_library {aaa_mode} from ' +\
        '[\?if=play_sorted sorted ]library|playlist][\?soft  - ]' +\
        '[\?if=continue C][\?if=follow F][\?if=repeat R][\?if=shuffle S]]'
}
```

@author lasers

SAMPLE OUTPUT
{'color': '#00FF00', 'full_text': '> Music For Programming - Big War'}

paused
{'color: '#FFFF00', 'full_text': '|| Music For Programming - Big War'}

stopped
{'color: '#FF0000', 'full_text': '.. Music For Programming - Big War'}

waiting
{'color: '#FF0000', 'full_text': '.. cmus: waiting for user input'}
"""

from __future__ import division


STRING_NOT_INSTALLED = "isn't installed"


class Py3status:
    """
    """
    # available configuration parameters
    button_next = None
    button_pause = 1
    button_previous = None
    button_repeat = None
    button_seek_backward = None
    button_seek_forward = None
    button_shuffle = None
    button_stop = 3
    button_volume_down = None
    button_volume_up = None
    cache_timeout = 5
    format = '[\?if=is_started [\?if=is_playing > ][\?if=is_paused \|\| ]' +\
        '[\?if=is_stopped .. ][[{artist}][\?soft  - ][{title}]' +\
        '|\?show cmus: waiting for user input]]'
    sleep_timeout = 20

    def post_config_hook(self):
        if not self.py3.check_commands('cmus-remote'):
            raise Exception(STRING_NOT_INSTALLED)

        self.color_stopped = self.py3.COLOR_STOPPED or self.py3.COLOR_BAD
        self.color_paused = self.py3.COLOR_PAUSED or self.py3.COLOR_DEGRADED
        self.color_playing = self.py3.COLOR_PLAYING or self.py3.COLOR_GOOD

        # check placeholders (an example to get raw value not available in data)
        self.use_follow = False
        format_contains = ['if=follow', 'if=!follow', '{follow}']
        for i in format_contains:
            if i in self.format:
                self.use_follow = True

    def _seconds_to_time(self, value):
        m, s = divmod(int(value), 60)
        h, m = divmod(m, 60)
        time = '%d:%02d:%02d' % (h, m, s)
        return time.lstrip('0').lstrip(':')

    def _get_cmus_data(self):
        try:
            data = self.py3.command_output(['cmus-remote', '--query'])
            is_started = True
        except:
            data = {}
            is_started = False
        return is_started, data

    def _organize_data(self, data):
        temporary = {}
        for line in data.splitlines():
            category, _, value = line.partition(' ')
            if category in ('set', 'tag'):
                key, _, value = value.partition(' ')
                temporary[key] = value
            else:
                temporary[category] = value
        return temporary

    def _manipulate_data(self, data):
        temporary = {}
        for key, value in data.items():
            # seconds to time
            if key in ('duration', 'position'):
                new_key = '%s%s' % (key, 'time')
                temporary[new_key] = self._seconds_to_time(value)
                temporary[key] = value
            # values to boolean
            elif value in ('true', 'enabled'):
                temporary[key] = True
            elif value in ('false', 'disabled'):
                temporary[key] = False
            # string not modified
            else:
                temporary[key] = value

        # stream to boolean
        if 'stream' in data:
            temporary['stream'] = True

        # cmus: don't mix cooked stuffs with raw stuffs.
        # (an example to get raw value not available in data)
        if self.use_follow:
            cmd = ['cmus-remote', '--raw', 'set follow']
            if 'true' in self.py3.command_output(cmd):
                temporary['follow'] = True
            else:
                temporary['follow'] = False

        return temporary

    def cmus(self):
        """
        """
        is_paused = is_playing = is_stopped = None
        cached_until = self.sleep_timeout
        color = self.py3.COLOR_BAD

        is_started, data = self._get_cmus_data()

        if is_started:
            cached_until = self.cache_timeout
            data = self._organize_data(data)
            data = self._manipulate_data(data)

            status = data.get('status')
            if status == 'playing':
                is_playing = True
                color = self.color_playing
            elif status == 'paused':
                is_paused = True
                color = self.color_paused
            elif status == 'stopped':
                is_stopped = True
                color = self.color_stopped

        return {
            'cached_until': self.py3.time_in(cached_until),
            'color': color,
            'full_text': self.py3.safe_format(self.format,
                                              dict(
                                                  is_paused=is_paused,
                                                  is_playing=is_playing,
                                                  is_started=is_started,
                                                  is_stopped=is_stopped,
                                                  **data
                                              ))
        }

    def on_click(self, event):
        """
        Control cmus with mouse clicks.
        """
        button = event['button']
        if button == self.button_pause:
            self.py3.command_run('cmus-remote --pause')
        elif button == self.button_stop:
            self.py3.command_run('cmus-remote --stop')
        elif button == self.button_next:
            self.py3.command_run('cmus-remote --next')
        elif button == self.button_previous:
            self.py3.command_run('cmus-remote --prev')
        elif button == self.button_repeat:
            self.py3.command_run('cmus-remote --repeat')
        elif button == self.button_shuffle:
            self.py3.command_run('cmus-remote --shuffle')
        elif button == self.button_seek_backward:
            self.py3.command_run('cmus-remote --seek -5')
        elif button == self.button_seek_forward:
            self.py3.command_run('cmus-remote --seek +5')
        elif button == self.button_volume_down:
            self.py3.command_run('cmus-remote --vol -5%')
        elif button == self.button_volume_up:
            self.py3.command_run('cmus-remote --vol +5%')
        else:
            self.py3.prevent_refresh()


if __name__ == "__main__":
    """
    Run module in test mode.
    """
    from py3status.module_test import module_test
    module_test(Py3status)
