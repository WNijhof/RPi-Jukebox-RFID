# RPi-Jukebox-RFID Version 3 - Eigen uitbreiding muziekbox
# Copyright (c) See file LICENSE in project root folder
"""
Spotify playback for the Jukebox

Plays Spotify playlists, albums, artists, tracks, podcasts and audiobooks on this box when a card is swiped.

How it works:

* librespot runs on the box as a Spotify Connect speaker (default name: *Muziekbox*) and plays into PulseAudio.
  Therefore, the Jukebox volume control and soft max volume also apply to Spotify.
* This module tells Spotify (via the Web API) what to play on that speaker.
* While Spotify is the active source, the regular player controls (``player.ctrl.toggle``, ``next``, ``prev``, ...)
  are routed to Spotify. So buttons, Web App controls and timers keep working unchanged.
  Playing local content (``play_card``, ``play_folder``, ...) hands control back to MPD.

Card registration: use the alias ``play_spotify`` with a Spotify link or URI as argument::

    '1234567890':
      alias: play_spotify
      args: [https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M, Kinderliedjes]

Setup: see ``eigen/SPOTIFY.md``
"""
import functools
import hashlib
import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Optional

import requests

import components.player
import jukebox.cfghandler
import jukebox.plugs as plugs
import jukebox.multitimer as multitimer
import jukebox.publishing as publishing

from .webapi import SpotifyWebApi, SpotifyApiError, SpotifyNotAuthorized

logger = logging.getLogger('jb.spotify')
cfg = jukebox.cfghandler.get_handler('jukebox')

#: URI types that are played as a context (and can be resumed)
CONTEXT_TYPES = ('playlist', 'album', 'artist', 'show', 'audiobook')
#: URI types that are played as a single item
ITEM_TYPES = ('track', 'episode')

_LINK_PATTERN = re.compile(
    r'open\.spotify\.com/(?:intl-[a-z]{2}(?:-[a-z]{2})?/)?(?:embed/)?'
    r'(playlist|album|artist|track|episode|show|audiobook)/([A-Za-z0-9]+)')
_URI_PATTERN = re.compile(r'^spotify:(playlist|album|artist|track|episode|show|audiobook):([A-Za-z0-9]+)$')


def normalize_uri(link: str) -> str:
    """Turn a Spotify share link or URI into a plain URI ``spotify:<type>:<id>``"""
    link = str(link).strip()
    match = _URI_PATTERN.match(link) or _LINK_PATTERN.search(link)
    if match is None:
        raise ValueError(f"Not a Spotify link or URI: '{link}'")
    return f"spotify:{match.group(1)}:{match.group(2)}"


class SpotifyCtrl:
    """Control Spotify playback on this box"""

    def __init__(self):
        self.device_name = cfg.setndefault('spotify', 'device_name', value='Muziekbox')
        token_file = cfg.setndefault('spotify', 'token_file', value='../../shared/settings/spotify_token.json')
        self.resume_file = cfg.setndefault('spotify', 'resume_file', value='../../shared/settings/spotify_resume.json')
        #: Default for cards without explicit setting
        self.default_shuffle = cfg.setndefault('spotify', 'shuffle', value=False)
        #: Continue a playlist/album/audiobook where it was left
        self.default_resume = cfg.setndefault('spotify', 'resume', value=True)
        #: What to do when the card of the content that is currently loaded is swiped again:
        #: 'play' (continue if paused), 'toggle' (play/pause), 'restart' (from the beginning), 'none'
        self.second_swipe = cfg.setndefault('spotify', 'second_swipe_action', value='play')
        self.poll_active_sec = cfg.setndefault('spotify', 'poll_interval_active_sec', value=2)
        self.poll_idle_sec = cfg.setndefault('spotify', 'poll_interval_idle_sec', value=15)
        coverart_cache_path = cfg.setndefault('webapp', 'coverart_cache_path',
                                              value='../../src/webapp/build/cover-cache')
        self.cover_cache = Path(coverart_cache_path).expanduser()

        self.api = SpotifyWebApi(os.path.abspath(token_file))
        self._lock = threading.RLock()
        self._device_id: Optional[str] = None
        self._active = False
        self._lost_count = 0
        self._last_poll = 0.0
        self._resume = self._load_resume()
        # Last known playback state (from the Web API)
        self.context_uri: Optional[str] = None
        self.item: Optional[dict] = None
        self.is_playing = False
        self.progress_ms = 0
        self.progress_at = time.monotonic()
        self.shuffle_state = False
        self.repeat_state = 'off'
        self.image_urls = {}

        # Originals of the MPD player methods, filled in by route_player_controls()
        self._mpd = {}

        self.status_thread = multitimer.GenericEndlessTimerClass('spotify.timer_status', 1.0, self._status_tick)
        self.status_thread.start()

    # -----------------------------------------------------------------------
    # Source handling
    # -----------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._active

    def _take_over(self):
        """Make Spotify the active source: silence MPD"""
        if not self._active:
            logger.info("Spotify becomes the active source")
            if 'pause' in self._mpd:
                try:
                    self._mpd['pause'](1)
                except Exception as e:
                    logger.debug(f"Could not pause MPD: {e}")
            self._active = True
            components.player.set_external_source_active(True)

    def release(self):
        """Hand control back to the local player (MPD)"""
        if self._active:
            logger.info("Spotify releases the player")
            self._save_resume_position()
            try:
                if self.is_playing:
                    self.api.pause(self._get_device_id())
            except Exception as e:
                logger.debug(f"Could not pause Spotify: {e}")
            self.is_playing = False
            self._active = False
            components.player.set_external_source_active(False)

    def route_player_controls(self, player_ctrl):
        """Route the regular player controls to Spotify while Spotify is the active source"""
        routed = ['play', 'pause', 'toggle', 'next', 'prev', 'stop', 'rewind', 'replay', 'replay_if_stopped',
                  'seek', 'shuffle', 'repeat', 'playerstatus', 'get_single_coverart']
        releasing = ['play_card', 'play_folder', 'play_album', 'play_single', 'resume']

        def make_routed(name, original):
            @functools.wraps(original)
            def wrapper(*args, **kwargs):
                if self._active:
                    return getattr(self, name)(*args, **kwargs)
                return original(*args, **kwargs)
            return wrapper

        def make_releasing(original):
            @functools.wraps(original)
            def wrapper(*args, **kwargs):
                self.release()
                return original(*args, **kwargs)
            return wrapper

        for name in routed + releasing:
            original = getattr(player_ctrl, name, None)
            if original is None:
                logger.warning(f"Player has no method '{name}', not routed")
                continue
            self._mpd[name] = original
            wrapper = make_routed(name, original) if name in routed else make_releasing(original)
            wrapper.plugs_callable = True
            # Instance attribute takes precedence over the class method when the plugs module looks it up
            setattr(player_ctrl, name, wrapper)
        logger.info(f"Player controls routed through Spotify: {', '.join(self._mpd.keys())}")

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _get_device_id(self, refresh: bool = False) -> str:
        with self._lock:
            if self._device_id is None or refresh:
                devices = self.api.devices()
                match = [d for d in devices if d.get('name', '').lower() == self.device_name.lower()]
                if not match:
                    names = ', '.join(d.get('name', '?') for d in devices) or 'none'
                    raise SpotifyApiError(404, f"Spotify Connect device '{self.device_name}' not found "
                                               f"(available: {names}). Is librespot running and logged in?")
                self._device_id = match[0]['id']
                logger.debug(f"Spotify device '{self.device_name}' has id {self._device_id}")
            return self._device_id

    def _call(self, func, *args, **kwargs):
        """Call a device-bound API function, re-resolving the device once if it went away"""
        try:
            return func(self._get_device_id(), *args, **kwargs)
        except SpotifyApiError as e:
            if e.status == 404:
                return func(self._get_device_id(refresh=True), *args, **kwargs)
            raise

    def _load_resume(self) -> dict:
        try:
            with open(self.resume_file) as f:
                return json.load(f)
        except (FileNotFoundError, ValueError):
            return {}

    def _save_resume_position(self):
        """Remember the position in the current context, so the card can continue there"""
        if self.context_uri and self.item and self.context_uri.split(':')[1] in CONTEXT_TYPES:
            self._resume[self.context_uri] = {'uri': self.item.get('uri'),
                                              'position_ms': self._elapsed_ms(),
                                              'saved': int(time.time())}
            try:
                with open(self.resume_file, 'w') as f:
                    json.dump(self._resume, f, indent=1)
            except OSError as e:
                logger.error(f"Could not save resume positions: {e}")

    def _elapsed_ms(self) -> int:
        elapsed = self.progress_ms
        if self.is_playing:
            elapsed += int((time.monotonic() - self.progress_at) * 1000)
        if self.item and self.item.get('duration_ms'):
            elapsed = min(elapsed, self.item['duration_ms'])
        return elapsed

    def _apply_state(self, state: Optional[dict]):
        with self._lock:
            if not state:
                self.is_playing = False
                return
            self.context_uri = (state.get('context') or {}).get('uri') or self.context_uri
            item = state.get('item')
            if item:
                self.item = item
                images = (item.get('album') or item.get('show') or {}).get('images') or item.get('images') or []
                if images:
                    self.image_urls[item['uri']] = images[0]['url']
            self.is_playing = bool(state.get('is_playing'))
            self.progress_ms = state.get('progress_ms') or 0
            self.progress_at = time.monotonic()
            self.shuffle_state = bool(state.get('shuffle_state'))
            self.repeat_state = state.get('repeat_state', 'off')

    def _refresh_state(self) -> Optional[dict]:
        state = self.api.playback_state()
        self._apply_state(state)
        self._last_poll = time.monotonic()
        return state

    def _status_tick(self):
        """Runs every second: poll Spotify (rate limited) and publish the player status while active"""
        if not self.api.is_authorized:
            return
        interval = self.poll_active_sec if self._active else self.poll_idle_sec
        if time.monotonic() - self._last_poll >= interval:
            try:
                state = self._refresh_state()
            except (SpotifyApiError, SpotifyNotAuthorized, requests.RequestException) as e:
                logger.debug(f"Spotify status poll failed: {e}")
                state = None
            device = (state or {}).get('device') or {}
            on_this_box = device.get('name', '').lower() == self.device_name.lower()
            if not self._active and on_this_box and state.get('is_playing'):
                # Somebody started Spotify on this box from the Spotify app
                self._take_over()
            elif self._active and state is not None and not on_this_box:
                # Playback was moved to another device, e.g. a phone
                self._lost_count += 1
                if self._lost_count >= 2:
                    logger.info("Spotify playback moved to another device")
                    self.is_playing = False
                    self._active = False
                    components.player.set_external_source_active(False)
            else:
                self._lost_count = 0
        if self._active:
            publishing.get_publisher().send('playerstatus', self.playerstatus())

    def exit(self):
        self._save_resume_position()
        self.status_thread.cancel()
        return self.status_thread.timer_thread

    # -----------------------------------------------------------------------
    # Card action
    # -----------------------------------------------------------------------

    @plugs.tag
    def play_card(self, uri: str, name: Optional[str] = None,
                  shuffle: Optional[bool] = None, resume: Optional[bool] = None):
        """Play a Spotify link or URI on this box (playlist, album, artist, track, episode, show, audiobook)

        :param uri: Spotify share link (https://open.spotify.com/...) or URI (spotify:playlist:...)
        :param name: Label to recognize the card in the Web App (not used for playback)
        :param shuffle: Shuffle on/off (default: setting spotify.shuffle)
        :param resume: Continue where this playlist/album was left (default: setting spotify.resume)
        """
        uri = normalize_uri(uri)
        kind = uri.split(':')[1]
        shuffle = self.default_shuffle if shuffle is None else bool(shuffle)
        resume = self.default_resume if resume is None else bool(resume)

        if self._active and uri == self.context_uri and self.second_swipe != 'restart':
            logger.info(f"Second swipe on {uri}: {self.second_swipe}")
            if self.second_swipe == 'toggle':
                return self.toggle()
            if self.second_swipe == 'play' and not self.is_playing:
                return self.play()
            return

        self._save_resume_position()
        self._take_over()

        offset_uri, position_ms = None, 0
        saved = self._resume.get(uri)
        if resume and saved and kind in CONTEXT_TYPES and not shuffle:
            offset_uri, position_ms = saved.get('uri'), saved.get('position_ms', 0)

        logger.info(f"Spotify: play {name or uri} (shuffle={shuffle}, resume={'yes' if offset_uri else 'no'})")
        context_uri = uri if kind in CONTEXT_TYPES else None
        uris = [uri] if kind in ITEM_TYPES else None
        try:
            self._call(self.api.play, context_uri=context_uri, uris=uris,
                       offset_uri=offset_uri, position_ms=position_ms)
        except SpotifyApiError as e:
            if not offset_uri:
                raise
            # The saved track is probably no longer in this playlist: start from the beginning
            logger.info(f"Resume not possible ({e}), starting from the beginning")
            self._call(self.api.play, context_uri=context_uri, uris=uris)
        with self._lock:
            self.context_uri = uri
            self.is_playing = True
        try:
            self._call(self.api.shuffle, shuffle)
        except SpotifyApiError as e:
            logger.warning(f"Could not set shuffle: {e}")
        # Make the next status tick fetch the new state right away
        self._last_poll = 0.0

    # -----------------------------------------------------------------------
    # Player controls (same signatures as the MPD player)
    # -----------------------------------------------------------------------

    @plugs.tag
    def play(self):
        self._take_over()
        self._call(self.api.play)
        self.is_playing = True
        self._last_poll = 0.0

    @plugs.tag
    def pause(self, state: int = 1):
        """Enforce pause to state (1: pause, 0: resume)"""
        if state:
            self._call(self.api.pause)
            self.progress_ms = self._elapsed_ms()
            self.is_playing = False
        else:
            self.play()
        self._last_poll = 0.0

    @plugs.tag
    def toggle(self):
        if self.is_playing:
            self.pause(1)
        else:
            self.play()

    @plugs.tag
    def stop(self):
        self.pause(1)

    @plugs.tag
    def next(self):
        self._call(self.api.next)
        self._last_poll = time.monotonic() - self.poll_active_sec + 0.5

    @plugs.tag
    def prev(self):
        self._call(self.api.previous)
        self._last_poll = time.monotonic() - self.poll_active_sec + 0.5

    @plugs.tag
    def rewind(self):
        """Restart the current playlist/album from the first track"""
        if self.context_uri:
            self._call(self.api.play, context_uri=self.context_uri)
            self.is_playing = True
            self._last_poll = 0.0

    @plugs.tag
    def replay(self):
        self.rewind()

    @plugs.tag
    def replay_if_stopped(self):
        if not self.is_playing:
            self.rewind()

    @plugs.tag
    def seek(self, new_time):
        self._call(self.api.seek, float(new_time) * 1000)
        self.progress_ms = int(float(new_time) * 1000)
        self.progress_at = time.monotonic()

    @plugs.tag
    def shuffle(self, option='toggle'):
        state = {'toggle': not self.shuffle_state, 'enable': True, 'disable': False}.get(option)
        if state is None:
            logger.error(f"'{option}' does not exist for 'shuffle'")
            return
        self._call(self.api.shuffle, state)
        self.shuffle_state = state

    @plugs.tag
    def repeat(self, option='toggle'):
        cycle = {'off': 'context', 'context': 'track', 'track': 'off'}
        state = {'toggle': cycle.get(self.repeat_state, 'off'),
                 'toggle_repeat': 'off' if self.repeat_state != 'off' else 'context',
                 'toggle_repeat_single': 'off' if self.repeat_state == 'track' else 'track',
                 'enable_repeat': 'context', 'enable_repeat_single': 'track', 'disable': 'off'}.get(option)
        if state is None:
            logger.error(f"'{option}' does not exist for 'repeat'")
            return
        self._call(self.api.repeat, state)
        self.repeat_state = state

    @plugs.tag
    def playerstatus(self) -> dict:
        """Player status in the same format as the MPD player publishes it"""
        with self._lock:
            item = self.item or {}
            if item.get('type') == 'episode':
                artist = (item.get('show') or {}).get('name', '')
                album = artist
            else:
                artist = ', '.join(a.get('name', '') for a in item.get('artists', []))
                album = (item.get('album') or {}).get('name', '')
            return {
                'state': 'play' if self.is_playing else ('pause' if item else 'stop'),
                'songid': item.get('id', ''),
                'title': item.get('name', ''),
                'artist': artist,
                'album': album,
                'file': item.get('uri', ''),
                'elapsed': f"{self._elapsed_ms() / 1000:.3f}",
                'duration': f"{item.get('duration_ms', 0) / 1000:.3f}",
                'random': '1' if self.shuffle_state else '0',
                'repeat': '0' if self.repeat_state == 'off' else '1',
                'single': '1' if self.repeat_state == 'track' else '0',
                'source': 'spotify',
                'context_uri': self.context_uri or '',
            }

    @plugs.tag
    def get_single_coverart(self, song_url):
        """Download the cover of a Spotify item into the Web App cover cache and return its file name"""
        url = self.image_urls.get(song_url)
        if not url:
            return ''
        filename = f"cover-spotify-{hashlib.sha256(url.encode()).hexdigest()[:32]}.jpg"
        path = self.cover_cache / filename
        if not path.exists():
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                self.cover_cache.mkdir(parents=True, exist_ok=True)
                path.write_bytes(resp.content)
            except (requests.RequestException, OSError) as e:
                logger.warning(f"Could not cache Spotify cover: {e}")
                return ''
        return filename

    # -----------------------------------------------------------------------
    # Information for the Web App / debugging
    # -----------------------------------------------------------------------

    @plugs.tag
    def list_playlists(self) -> list:
        """Playlists of the authorized account (own, followed and collaborative)"""
        return [{'name': p.get('name', ''),
                 'uri': p.get('uri', ''),
                 'owner': (p.get('owner') or {}).get('display_name', ''),
                 'collaborative': p.get('collaborative', False)}
                for p in self.api.my_playlists()]

    @plugs.tag
    def get_state(self) -> dict:
        return {'authorized': self.api.is_authorized,
                'active': self._active,
                'device_name': self.device_name,
                'status': self.playerstatus()}

    @plugs.tag
    def list_devices(self) -> list:
        return [{'name': d.get('name'), 'type': d.get('type'), 'is_active': d.get('is_active')}
                for d in self.api.devices()]


spotify_ctrl: SpotifyCtrl


@plugs.initialize
def initialize():
    global spotify_ctrl
    spotify_ctrl = SpotifyCtrl()
    plugs.register(spotify_ctrl, name='ctrl')
    if not spotify_ctrl.api.is_authorized:
        logger.warning("Spotify is not authorized yet. Run installation/components/setup_spotify.sh auth")


@plugs.finalize
def finalize():
    global spotify_ctrl
    try:
        player_ctrl = plugs.get('player', 'ctrl')
    except NameError:
        logger.error("No player loaded: Spotify works from cards only, buttons are not routed")
        return
    spotify_ctrl.route_player_controls(player_ctrl)


@plugs.atexit
def atexit(**ignored_kwargs):
    global spotify_ctrl
    return spotify_ctrl.exit()
