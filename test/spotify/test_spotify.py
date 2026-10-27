# RPi-Jukebox-RFID Version 3 - Eigen uitbreiding muziekbox
# Copyright (c) See file LICENSE in project root folder
import os
import sys
import types
from unittest import mock

import pytest

# In case this is run locally from
sys.path.append(os.path.abspath('../../src/jukebox'))

# Avoid the ZeroMQ publisher and real timer threads
_publisher = mock.MagicMock()
sys.modules.setdefault('jukebox.publishing', types.SimpleNamespace(get_publisher=lambda: _publisher))

import jukebox.plugs  # noqa: E402
jukebox.plugs.ALLOW_DIRECT_IMPORTS = True
import jukebox.multitimer  # noqa: E402
import components.player  # noqa: E402
import components.spotify as spotify  # noqa: E402
from components.spotify.webapi import SpotifyApiError  # noqa: E402


class FakeApi:
    """Records the Web API calls instead of doing them"""

    def __init__(self):
        self.calls = []
        self.is_authorized = True
        self.fail_offset = False

    def devices(self):
        return [{'id': 'phone', 'name': 'Telefoon'}, {'id': 'box', 'name': 'Muziekbox'}]

    def playback_state(self):
        return None

    def play(self, device_id, context_uri=None, uris=None, offset_uri=None, position_ms=0):
        if offset_uri and self.fail_offset:
            raise SpotifyApiError(404, 'track not in context')
        self.calls.append(('play', device_id, context_uri, uris, offset_uri, position_ms))

    def __getattr__(self, name):
        # pause, next, previous, shuffle, ...
        return lambda device_id, *args: self.calls.append((name, device_id, *args))


class FakeMpd:
    def __init__(self):
        self.calls = []

    def _record(self, name, *args):
        self.calls.append((name, *args))
        return name

    def play(self):
        return self._record('play')

    def pause(self, state=1):
        return self._record('pause', state)

    def toggle(self):
        return self._record('toggle')

    def next(self):
        return self._record('next')

    def prev(self):
        return self._record('prev')

    def stop(self):
        return self._record('stop')

    def rewind(self):
        return self._record('rewind')

    def replay(self):
        return self._record('replay')

    def replay_if_stopped(self):
        return self._record('replay_if_stopped')

    def seek(self, new_time):
        return self._record('seek', new_time)

    def shuffle(self, option='toggle'):
        return self._record('shuffle', option)

    def repeat(self, option='toggle'):
        return self._record('repeat', option)

    def playerstatus(self):
        return {'state': 'stop'}

    def get_single_coverart(self, song_url):
        return self._record('cover', song_url)

    def play_card(self, folder, recursive=False):
        return self._record('play_card', folder)

    def play_folder(self, folder, recursive=False):
        return self._record('play_folder', folder)

    def play_album(self, albumartist, album):
        return self._record('play_album', albumartist, album)

    def play_single(self, song_url):
        return self._record('play_single', song_url)

    def resume(self):
        return self._record('resume')


@pytest.fixture
def ctrl(tmp_path):
    cfg = spotify.cfg
    cfg.setn('spotify', 'resume_file', value=str(tmp_path / 'resume.json'))
    cfg.setn('spotify', 'token_file', value=str(tmp_path / 'token.json'))
    with mock.patch.object(jukebox.multitimer, 'GenericEndlessTimerClass'):
        c = spotify.SpotifyCtrl()
    c.api = FakeApi()
    mpd = FakeMpd()
    c.route_player_controls(mpd)
    yield c, mpd
    components.player.set_external_source_active(False)


@pytest.mark.parametrize('link, uri', [
    ('https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=abc123', 'spotify:playlist:37i9dQZF1DXcBWIGoYBM5M'),
    ('https://open.spotify.com/intl-nl/album/1A2GTWGtFfWp7KSQTwWOyo', 'spotify:album:1A2GTWGtFfWp7KSQTwWOyo'),
    ('  spotify:track:4uLU6hMCjMI75M1A2tKUQC ', 'spotify:track:4uLU6hMCjMI75M1A2tKUQC'),
    ('https://open.spotify.com/show/5CfCWKI5pZ28U0uOzXkDHe', 'spotify:show:5CfCWKI5pZ28U0uOzXkDHe'),
])
def test_normalize_uri(link, uri):
    assert spotify.normalize_uri(link) == uri


def test_normalize_uri_rejects_other_links():
    with pytest.raises(ValueError):
        spotify.normalize_uri('https://www.youtube.com/watch?v=123')


def test_controls_go_to_mpd_while_spotify_inactive(ctrl):
    c, mpd = ctrl
    assert mpd.toggle() == 'toggle'
    assert mpd.next() == 'next'
    assert c.api.calls == []
    # Routed methods stay callable through the plugs interface
    assert mpd.toggle.plugs_callable is True


def test_card_takes_over_and_routes_controls(ctrl):
    c, mpd = ctrl
    c.play_card('https://open.spotify.com/playlist/abc', 'Kinderliedjes')

    assert c.is_active
    assert components.player.is_external_source_active()
    assert ('pause', 1) in mpd.calls  # MPD is silenced
    assert c.api.calls[0] == ('play', 'box', 'spotify:playlist:abc', None, None, 0)
    assert ('shuffle', 'box', False) in c.api.calls

    mpd.calls.clear()
    mpd.toggle()  # playing -> pause
    mpd.next()
    assert ('pause', 'box') in c.api.calls
    assert ('next', 'box') in c.api.calls
    assert mpd.calls == []


def test_local_content_releases_spotify(ctrl):
    c, mpd = ctrl
    c.play_card('spotify:album:xyz')
    mpd.play_folder('Nijntje')

    assert not c.is_active
    assert not components.player.is_external_source_active()
    assert ('pause', 'box') in c.api.calls
    assert ('play_folder', 'Nijntje') in mpd.calls


def test_track_is_played_as_single_item(ctrl):
    c, _ = ctrl
    c.play_card('spotify:track:t1')
    assert c.api.calls[0] == ('play', 'box', None, ['spotify:track:t1'], None, 0)


def test_resume_where_left(ctrl):
    c, _ = ctrl
    c.play_card('spotify:playlist:p1')
    c.item = {'uri': 'spotify:track:t7', 'duration_ms': 200000}
    c.is_playing = False
    c.progress_ms = 61000
    c.play_card('spotify:playlist:p2')  # saves position of p1
    c.api.calls.clear()

    c.play_card('spotify:playlist:p1')
    assert c.api.calls[0] == ('play', 'box', 'spotify:playlist:p1', None, 'spotify:track:t7', 61000)


def test_resume_falls_back_to_start(ctrl):
    c, _ = ctrl
    c._resume['spotify:playlist:p1'] = {'uri': 'spotify:track:gone', 'position_ms': 5000}
    c.api.fail_offset = True
    c.play_card('spotify:playlist:p1')
    assert c.api.calls[0] == ('play', 'box', 'spotify:playlist:p1', None, None, 0)


def test_second_swipe_continues_when_paused(ctrl):
    c, _ = ctrl
    c.play_card('spotify:playlist:p1')
    c.is_playing = False
    c.api.calls.clear()

    c.play_card('spotify:playlist:p1')
    assert c.api.calls == [('play', 'box', None, None, None, 0)]

    c.api.calls.clear()
    c.play_card('spotify:playlist:p1')  # already playing: nothing happens
    assert c.api.calls == []


def test_playerstatus_has_mpd_format(ctrl):
    c, mpd = ctrl
    c.play_card('spotify:playlist:p1')
    c.item = {'id': 't1', 'uri': 'spotify:track:t1', 'name': 'Hoedje van papier', 'duration_ms': 90000,
              'artists': [{'name': 'Kinderkoor'}], 'album': {'name': 'Liedjes'}}
    status = mpd.playerstatus()  # routed through Spotify
    assert status['state'] == 'play'
    assert status['title'] == 'Hoedje van papier'
    assert status['artist'] == 'Kinderkoor'
    assert status['file'] == 'spotify:track:t1'
    assert status['duration'] == '90.000'
