# RPi-Jukebox-RFID Version 3 - Eigen uitbreiding muziekbox
# Copyright (c) See file LICENSE in project root folder
"""
Minimal Spotify Web API client (Authorization Code flow with PKCE)

Only uses ``requests``, which is already a Jukebox dependency. The refresh token is stored in a
JSON file on the box (default: ``shared/settings/spotify_token.json``), which is never part of the repository.

PKCE means no client secret is needed: only the Client ID of your app from the Spotify Developer Dashboard.
"""
import base64
import hashlib
import json
import logging
import os
import secrets
import threading
import time
import urllib.parse
from typing import Optional

import requests

logger = logging.getLogger('jb.spotify.webapi')

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_URL = 'https://api.spotify.com/v1'

#: Spotify only accepts loopback IP redirect URIs for plain http (not 'localhost')
DEFAULT_REDIRECT_URI = 'http://127.0.0.1:8888/callback'

SCOPES = ' '.join([
    'user-read-playback-state',
    'user-modify-playback-state',
    'user-read-currently-playing',
    'playlist-read-private',
    'playlist-read-collaborative',
    'user-library-read',
])


class SpotifyApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"Spotify API error {status}: {message}")
        self.status = status


class SpotifyNotAuthorized(Exception):
    pass


# ---------------------------------------------------------------------------
# One-time authorization (used by run_spotify_auth.py)
# ---------------------------------------------------------------------------

def make_pkce_pair():
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    return verifier, challenge


def build_authorize_url(client_id: str, challenge: str, state: str, redirect_uri: str = DEFAULT_REDIRECT_URI) -> str:
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'code_challenge_method': 'S256',
        'code_challenge': challenge,
        'scope': SCOPES,
        'state': state,
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code(client_id: str, code: str, verifier: str, redirect_uri: str = DEFAULT_REDIRECT_URI) -> dict:
    resp = requests.post(TOKEN_URL, timeout=15, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'code_verifier': verifier,
    })
    if resp.status_code != 200:
        raise SpotifyApiError(resp.status_code, resp.text)
    return resp.json()


def save_token_file(token_file: str, client_id: str, token: dict):
    data = {
        'client_id': client_id,
        'refresh_token': token['refresh_token'],
        'access_token': token.get('access_token'),
        'expires_at': time.time() + token.get('expires_in', 0),
    }
    # Create the file with owner-only permissions: it grants access to the Spotify account.
    # Write to a temporary file and rename, so a process reading the file never sees half of it
    tmp_file = f"{token_file}.tmp"
    fd = os.open(tmp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_file, token_file)


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class SpotifyWebApi:
    """Thread-safe, auto-refreshing access to the Spotify Web API"""

    def __init__(self, token_file: str):
        self.token_file = token_file
        self._lock = threading.RLock()
        self._session = requests.Session()
        self._client_id = None
        self._refresh_token = None
        self._access_token = None
        self._expires_at = 0.0
        self._loaded_mtime = None
        self._load()

    @property
    def is_authorized(self) -> bool:
        with self._lock:
            self._reload_if_changed()
            return self._refresh_token is not None

    def _file_mtime(self) -> Optional[float]:
        try:
            return os.path.getmtime(self.token_file)
        except OSError:
            return None

    def _reload_if_changed(self):
        # Another process may have written the file: a new login (setup_spotify.sh auth) or a refresh,
        # which rotates the refresh token and makes the one in memory invalid
        if self._file_mtime() != self._loaded_mtime:
            logger.info("Spotify token file changed on disk, reloading")
            self._load()

    def _load(self):
        self._loaded_mtime = self._file_mtime()
        try:
            with open(self.token_file) as f:
                data = json.load(f)
            self._client_id = data['client_id']
            self._refresh_token = data['refresh_token']
            self._access_token = data.get('access_token')
            self._expires_at = data.get('expires_at', 0.0)
        except FileNotFoundError:
            logger.warning(f"No Spotify token file '{self.token_file}'. Run installation/components/setup_spotify.sh auth")
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid Spotify token file '{self.token_file}': {e}")

    def _refresh(self):
        if not self.is_authorized:
            raise SpotifyNotAuthorized("Spotify is not authorized. Run installation/components/setup_spotify.sh auth")
        resp = self._session.post(TOKEN_URL, timeout=15, data={
            'grant_type': 'refresh_token',
            'refresh_token': self._refresh_token,
            'client_id': self._client_id,
        })
        if resp.status_code != 200:
            raise SpotifyApiError(resp.status_code, f"Token refresh failed: {resp.text}")
        token = resp.json()
        self._access_token = token['access_token']
        self._expires_at = time.time() + token.get('expires_in', 3600)
        # With PKCE, Spotify rotates the refresh token: always store the newest one
        if token.get('refresh_token'):
            self._refresh_token = token['refresh_token']
        save_token_file(self.token_file, self._client_id,
                        {'refresh_token': self._refresh_token, 'access_token': self._access_token,
                         'expires_in': self._expires_at - time.time()})
        self._loaded_mtime = self._file_mtime()
        logger.debug("Spotify access token refreshed")

    def _token(self) -> str:
        with self._lock:
            self._reload_if_changed()
            if self._access_token is None or time.time() > self._expires_at - 60:
                self._refresh()
            return self._access_token

    def request(self, method: str, path: str, params: Optional[dict] = None, body: Optional[dict] = None,
                _retry: bool = True):
        """Do an API call. Returns the decoded JSON body, or None for empty responses"""
        with self._lock:
            resp = self._session.request(method, f"{API_URL}{path}", params=params, json=body, timeout=10,
                                         headers={'Authorization': f"Bearer {self._token()}"})
        if resp.status_code == 401 and _retry:
            # Token revoked or expired early: force a refresh once
            with self._lock:
                self._access_token = None
            return self.request(method, path, params, body, _retry=False)
        if resp.status_code == 429 and _retry:
            wait = min(int(resp.headers.get('Retry-After', '1')), 10)
            logger.warning(f"Spotify rate limit hit, retrying in {wait} s")
            time.sleep(wait)
            return self.request(method, path, params, body, _retry=False)
        if resp.status_code >= 400:
            try:
                message = resp.json().get('error', {}).get('message', resp.text)
            except ValueError:
                message = resp.text
            raise SpotifyApiError(resp.status_code, message)
        if not resp.content:
            return None
        try:
            return resp.json()
        except ValueError:
            return None

    # Convenience wrappers --------------------------------------------------

    def devices(self) -> list:
        return (self.request('GET', '/me/player/devices') or {}).get('devices', [])

    def playback_state(self) -> Optional[dict]:
        """Current playback state, or None when nothing is active on the account"""
        return self.request('GET', '/me/player', params={'additional_types': 'track,episode'})

    def play(self, device_id: str, context_uri: Optional[str] = None, uris: Optional[list] = None,
             offset_uri: Optional[str] = None, position_ms: int = 0):
        body = {}
        if context_uri:
            body['context_uri'] = context_uri
        if uris:
            body['uris'] = uris
        if offset_uri:
            body['offset'] = {'uri': offset_uri}
        if position_ms:
            body['position_ms'] = int(position_ms)
        self.request('PUT', '/me/player/play', params={'device_id': device_id}, body=body or None)

    def pause(self, device_id: str):
        self.request('PUT', '/me/player/pause', params={'device_id': device_id})

    def next(self, device_id: str):
        self.request('POST', '/me/player/next', params={'device_id': device_id})

    def previous(self, device_id: str):
        self.request('POST', '/me/player/previous', params={'device_id': device_id})

    def seek(self, device_id: str, position_ms: int):
        self.request('PUT', '/me/player/seek', params={'device_id': device_id, 'position_ms': int(position_ms)})

    def shuffle(self, device_id: str, state: bool):
        self.request('PUT', '/me/player/shuffle', params={'device_id': device_id, 'state': str(bool(state)).lower()})

    def repeat(self, device_id: str, state: str):
        self.request('PUT', '/me/player/repeat', params={'device_id': device_id, 'state': state})

    def my_playlists(self, limit: int = 200) -> list:
        """Playlists the account owns or follows (incl. collaborative playlists)"""
        result = []
        params = {'limit': 50, 'offset': 0}
        while len(result) < limit:
            page = self.request('GET', '/me/playlists', params=params) or {}
            items = page.get('items', [])
            result.extend(i for i in items if i)
            if not page.get('next') or not items:
                break
            params['offset'] += len(items)
        return result[:limit]
