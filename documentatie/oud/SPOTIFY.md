# Spotify op de muziekbox

De kinderen houden een kaart tegen de box en er start een Spotify-playlist. Jullie beheren de
playlists vanaf je eigen Spotify-account. De knoppen op de box (play/pauze, vorige, volgende,
volume) bedienen Spotify. Het maximale volume van de box blijft gelden.

## Zo werkt het

```text
 kaart ──► Phoniebox ──(Spotify Web API: "speel playlist X op Muziekbox")──► Spotify
                                                                              │
 speaker ◄── PulseAudio ◄── librespot ("Muziekbox", Spotify Connect) ◄────────┘
```

- **librespot** draait op de Pi en verschijnt in de Spotify-app als luidspreker **Muziekbox**.
- De **Spotify-module** (`src/jukebox/components/spotify/`) vertelt Spotify via de Web API wat er
  op die luidspreker moet spelen.
- Zolang Spotify speelt, gaan alle bedieningen van de speler naar Spotify: knoppen, webapp,
  slaaptimer en tweede keer een kaart scannen.
- librespot speelt af via PulseAudio, net als de rest van de box. Daardoor werken de
  volumeknoppen en het maximumvolume (`soft_max_volume`) ook voor Spotify. De volumeschuif in de
  Spotify-app is uitgeschakeld (`--volume-ctrl fixed`), zodat niemand het maximum omzeilt.

## 1. Wat je nodig hebt

- **Spotify Premium** voor het account van de box. Zonder Premium kan geen enkele externe speler
  afspelen. Een account binnen een **Premium Family**-abonnement is prima.
- Een **apart account voor de box**, bijvoorbeeld een familielid-account "Kinderen". Gebruik
  een gewoon account, geen Spotify Kids-app-account: of dat met Connect en de Web API werkt, is twijfelachtig.
- De box moet internet hebben (wifi).

## 2. Playlists delen

1. Maak de playlists vanaf je eigen account, bijvoorbeeld "Slaapliedjes" of "Feestje".
2. Maak ze **gezamenlijk**: open de playlist → ⋯ → *Samenwerken* / *Uitnodigen*. Stuur de
   uitnodiging naar je partner en naar het account van de box, of laat het box-account de
   playlist volgen.
3. Daarna staat de playlist in de bibliotheek van het box-account en verschijnt hij in de keuzelijst
   in de webapp. Iedereen met toegang kan nummers toevoegen of weghalen. De kaart speelt altijd de
   actuele versie, omdat er alleen een verwijzing naar de playlist op de kaart staat.

Een kaart kan ook een album, artiest, los nummer, podcast of luisterboek starten. Plak dan de link.

## 3. Spotify-app aanmaken (eenmalig, 5 minuten)

De box heeft een eigen "app-sleutel" (Client ID) nodig om de Web API te gebruiken.

1. Ga naar <https://developer.spotify.com/dashboard> en log in. Dat mag met je eigen account.
2. Klik op **Create app**:
   - App name: `Muziekbox`
   - App description: `Muziekbox voor de kinderen`
   - Redirect URI: **`http://127.0.0.1:8888/callback`** (precies zo, en klik op *Add*)
   - Bij "Which API/SDKs are you planning to use": vink **Web API** aan
   - Ga akkoord met de voorwaarden en klik op *Save*
3. Open de app → **Settings** en kopieer de **Client ID**. Een Client Secret is niet nodig;
   de box gebruikt de veiligere PKCE-methode.
4. Heb je de app met een ander account aangemaakt dan het box-account? Voeg het box-account dan toe
   onder **User Management**, met de naam en het e-mailadres van dat Spotify-account.
   Apps in "development mode" werken alleen voor accounts op die lijst.

## 4. Installeren op de Pi

Dit doe je nadat de Phoniebox-installatie uit de bouwhandleiding (hoofdstuk 5) klaar is
en het geluid werkt. Log in via SSH:

```bash
cd ~/RPi-Jukebox-RFID/installation/components
./setup_spotify.sh
```

Het script doet drie dingen:

1. **librespot installeren** via [raspotify](https://dtcooper.github.io/raspotify/) en als
   achtergronddienst `librespot.service` starten (naam: *Muziekbox*).
2. Daarna vraagt het je om op je telefoon **in de Spotify-app, ingelogd als het box-account,
   eenmalig de luidspreker "Muziekbox" te kiezen**. Speel even iets af en druk dan op Enter.
   librespot onthoudt deze inlog voortaan.
3. **Het account koppelen aan de Web API**:
   - Plak de Client ID.
   - Open de link die verschijnt in de browser op je pc en log in als het **box-account**.
   - Na *Akkoord* krijg je een foutpagina van `127.0.0.1`. **Dat is de bedoeling.**
     Kopieer het volledige adres uit de adresbalk en plak het in de SSH-terminal.
   - Het script toont de Spotify Connect-apparaten die het account ziet. *Muziekbox* moet erbij staan.

Herstart daarna de box-software:

```bash
systemctl --user restart jukebox-daemon
```

De koppeling wordt opgeslagen in `shared/settings/spotify_token.json`, alleen leesbaar voor jouw
gebruiker. Dit bestand staat **niet** in Git.

Later alleen één onderdeel opnieuw doen:

```bash
./setup_spotify.sh librespot   # alleen de luidspreker (her)installeren
./setup_spotify.sh auth        # ander account koppelen, of de koppeling herstellen
```

Een andere naam voor de luidspreker? Gebruik `DEVICE_NAME="Box Kinderkamer" ./setup_spotify.sh librespot`
en zet dezelfde naam in `shared/settings/jukebox.yaml` bij `spotify: device_name:`.

## 5. Kaart koppelen

1. Open de webapp: `http://muziekbox.local` → **Cards** → registreer een nieuwe kaart.
2. Houd de kaart tegen de box.
3. Kies bij de actie **Spotify**.
4. Kies een playlist uit de lijst, of plak een Spotify-link (in de app: *Delen → Link kopiëren*).
5. Geef de kaart een naam, zodat je hem in het overzicht herkent, en sla op.

Wil je kaarten met de hand invoeren? Dat kan in `shared/settings/cards.yaml`:

```yaml
'1234567890':
  alias: play_spotify
  args: [https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M, Slaapliedjes]
'1234567891':
  alias: play_spotify
  # Per kaart afwijken van de standaard: shuffle aan, niet hervatten
  args: [spotify:album:1A2GTWGtFfWp7KSQTwWOyo, Feestje, true, false]
```

## 6. Gedrag en instellingen

| Situatie | Wat er gebeurt |
|---|---|
| Kaart scannen | Playlist start op de box. Was die playlist eerder halverwege, dan gaat hij verder waar hij was (`resume`) |
| Dezelfde kaart nog eens | Gaat verder als hij op pauze stond, en doet verder niets (`second_swipe_action: play`) |
| Andere kaart | De positie van de vorige playlist wordt onthouden en de nieuwe start |
| Play/pauze, vorige, volgende | Bedient Spotify |
| Volume +/− | Volume van de box, nooit boven `soft_max_volume` |
| Jij kiest "Muziekbox" in je eigen Spotify-app | De box neemt het over en de knoppen werken ook dan |
| Jij haalt de muziek naar je telefoon | De box laat Spotify los |
| Lokale MP3-kaart (als je die ooit gebruikt) | Spotify pauzeert en de lokale speler neemt over |

De instellingen staan in `shared/settings/jukebox.yaml` onder `spotify:`. Stop eerst de dienst,
pas het bestand aan en start de dienst weer:

```yaml
spotify:
  device_name: Muziekbox        # naam van de librespot-luidspreker
  shuffle: false                # standaard shuffle voor kaarten
  resume: true                  # verder waar je was
  second_swipe_action: play     # play | toggle | restart | none
```

## 7. Problemen oplossen

| Probleem | Oplossing |
|---|---|
| Kaart doet niets, log zegt *device 'Muziekbox' not found* | librespot draait niet of is niet ingelogd. Controleer met `systemctl --user status librespot` en kies de box nog één keer als luidspreker in de Spotify-app (box-account) |
| *Spotify is not authorized* | `./setup_spotify.sh auth` opnieuw uitvoeren |
| *Premium required* | Het box-account heeft geen Premium |
| Spotify speelt, maar zonder geluid | Bekijk `journalctl --user -u librespot -f`. Werkt de pulseaudio-backend niet, verander dan in `~/.config/systemd/user/librespot.service` `--backend pulseaudio` in `--backend alsa --device pulse`, en voer `systemctl --user daemon-reload && systemctl --user restart librespot` uit |
| Keuzelijst met playlists blijft leeg | Volgt het box-account de playlists? Herlaad de webapp. Plakken van een link werkt altijd |
| Na een tijd werkt het niet meer | Kijk in `shared/logs/errors.log`. Is de koppeling ingetrokken (bijv. wachtwoord gewijzigd), voer dan `./setup_spotify.sh auth` opnieuw uit |

Log volgen: `tail -f ~/RPi-Jukebox-RFID/shared/logs/app.log | grep -i spotify`

## 8. Voor ontwikkelaars: wat is er aangepast

Zo weet je waar je op moet letten bij het binnenhalen van nieuwe Phoniebox-versies (`git merge upstream/future3/main`).

| Bestand | Wijziging |
|---|---|
| `src/jukebox/components/spotify/` | **Nieuw:** Spotify-module (`__init__.py`) en Web API-client (`webapi.py`) |
| `src/jukebox/run_spotify_auth.py` | **Nieuw:** eenmalige koppeling met het account |
| `installation/components/setup_spotify.sh` | **Nieuw:** installatie van librespot en koppeling |
| `resources/default-services/librespot.service` | **Nieuw:** user service voor librespot |
| `test/spotify/test_spotify.py` | **Nieuw:** tests |
| `src/webapp/src/components/Cards/controls/actions/spotify/` | **Nieuw:** Spotify-keuze bij kaarten |
| `src/jukebox/components/player/__init__.py` | Vlag "externe bron actief" toegevoegd |
| `src/jukebox/components/playermpd/__init__.py` | 3 regels: geen MPD-status publiceren als Spotify actief is |
| `src/jukebox/components/rpc_command_alias.py` | Alias `play_spotify` |
| `resources/default-settings/jukebox.default.yaml` | Module `spotify` en sectie `spotify:` |
| `src/webapp/src/config.js`, `commands/index.js`, `controls-selector.js`, `public/locales/*/translation.json` | Spotify-actie in de webapp |

Alle wijzigingen in bestaande bestanden zijn gemarkeerd met `Eigen uitbreiding muziekbox`.

De routering van de knoppen werkt zo: bij het opstarten (`finalize`) vervangt de Spotify-module
de methodes van `player.ctrl` (zoals `toggle`, `next` en `prev`) door een tussenlaag. Die stuurt
door naar Spotify als Spotify actief is, en anders naar MPD. Daardoor hoeft `gpio.yaml` niet aangepast.

Tests draaien: `./run_pytest.sh test/spotify` op de Pi, of `python -m pytest test/spotify` met een venv.
