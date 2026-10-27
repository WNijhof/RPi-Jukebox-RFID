#!/usr/bin/env python
"""
Setup tool to connect the Jukebox to a Spotify account (eigen uitbreiding muziekbox)

Run this once (via ``installation/components/setup_spotify.sh``). It stores a refresh token in
``shared/settings/spotify_token.json``. Re-run it to switch to another Spotify account.

The box works headless, so the login happens in the browser on your PC or phone:
after logging in, Spotify redirects to http://127.0.0.1:8888/callback, which shows an error page.
That is expected: copy the full address from the address bar and paste it here.
"""
import argparse
import os
import secrets
import sys
import urllib.parse

import jukebox.plugs
jukebox.plugs.ALLOW_DIRECT_IMPORTS = True
from components.spotify import webapi  # noqa: E402


def main():
    script_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    token_file_default = os.path.abspath(os.path.join(script_path, '../../shared/settings/spotify_token.json'))

    parser = argparse.ArgumentParser(description='Connect the Jukebox to a Spotify account')
    parser.add_argument('-c', '--client-id', help='Client ID of your app in the Spotify Developer Dashboard')
    parser.add_argument('-f', '--token-file', default=token_file_default, help='Where to store the token')
    parser.add_argument('-r', '--redirect-uri', default=webapi.DEFAULT_REDIRECT_URI,
                        help='Redirect URI as registered in the Spotify Developer Dashboard')
    args = parser.parse_args()

    print("\n=== Muziekbox: koppelen met Spotify ===\n")
    client_id = args.client_id or input("Client ID van je Spotify-app: ").strip()
    if not client_id:
        sys.exit("Geen Client ID opgegeven.")

    verifier, challenge = webapi.make_pkce_pair()
    state = secrets.token_urlsafe(16)
    url = webapi.build_authorize_url(client_id, challenge, state, args.redirect_uri)

    print("\n1. Open deze link in de browser op je pc of telefoon en log in met het Spotify-account van de box:\n")
    print(f"   {url}\n")
    print("2. Na 'Akkoord' kom je op een foutpagina (127.0.0.1 weigert verbinding). Dat klopt.")
    print("   Kopieer het VOLLEDIGE adres uit de adresbalk en plak het hieronder.\n")
    redirected = input("Adres: ").strip()

    query = urllib.parse.parse_qs(urllib.parse.urlparse(redirected).query)
    if 'error' in query:
        sys.exit(f"Spotify meldt een fout: {query['error'][0]}")
    if query.get('state', [''])[0] != state:
        sys.exit("Het adres hoort niet bij deze inlogpoging (state klopt niet). Probeer het opnieuw.")
    code = query.get('code', [''])[0]
    if not code:
        sys.exit("Geen code gevonden in het adres.")

    token = webapi.exchange_code(client_id, code, verifier, args.redirect_uri)
    os.makedirs(os.path.dirname(args.token_file), exist_ok=True)
    webapi.save_token_file(args.token_file, client_id, token)
    print(f"\nGelukt! Token opgeslagen in {args.token_file}")

    api = webapi.SpotifyWebApi(args.token_file)
    devices = api.devices()
    names = ', '.join(d.get('name', '?') for d in devices) or 'geen'
    print(f"Spotify Connect-apparaten die dit account nu ziet: {names}")
    print("\nHerstart de Jukebox om Spotify te gebruiken:  systemctl --user restart jukebox-daemon\n")


if __name__ == '__main__':
    main()
