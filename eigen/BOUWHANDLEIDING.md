# Bouwhandleiding muziekbox (Phoniebox v3 op Raspberry Pi 3B)

Een oplaadbare muziekbox die de kinderen zelf bedienen met NFC-kaarten en grote knoppen.
Kaarten starten Spotify-playlists ([SPOTIFY.md](SPOTIFY.md)) en de box draait op een accu
([ACCU.md](ACCU.md)). Wij beheren hem via de webpagina op de telefoon. De software is onze eigen kopie
van [Phoniebox](https://github.com/MiczFlor/RPi-Jukebox-RFID), branch `future3/main`.

Inhoud:

1. [Boodschappenlijst](#1-boodschappenlijst)
2. [Eigen Git-repository opzetten](#2-eigen-git-repository-opzetten)
3. [Pinplan: wat gaat waar](#3-pinplan-wat-gaat-waar)
4. [Aansluiten, stap voor stap](#4-aansluiten-stap-voor-stap)
5. [Software installeren](#5-software-installeren)
6. [Configureren en testen](#6-configureren-en-testen)
7. [Kastje printen met de Prusa](#7-kastje-printen-met-de-prusa)
8. [Spotify](#8-spotify)
9. [Problemen oplossen](#9-problemen-oplossen)

---

## 1. Boodschappenlijst

| # | Onderdeel | Let op | Ca. prijs |
|---|---|---|---|
| 1 | Raspberry Pi 3B | Hebben we al | – |
| 1 | MicroSD-kaart 32 GB, A1 | Samsung EVO / SanDisk | € 8 |
| 1 | **PiSugar 3 Plus** (accu 5000 mAh, USB-C) | Onder de Pi, laden tijdens het spelen, eigen aan/uit-knop. Zie [ACCU.md](ACCU.md). Tinytronics (NL) | € 51 |
| 1 | USB-C-lader 5 V / 3 A | Bijv. de officiële Raspberry Pi USB-C-voeding. Om de accu te laden | € 10 |
| 1 | **RC522 RFID-lezer** (13,56 MHz, SPI) | Meestal met losse pinheaders, die moet je solderen | € 4 |
| 20–50 | **Mifare Classic 1K (S50)** kaarten, stickers of sleutelhangers | ⚠️ **Géén NTAG213/215!** De RC522-driver leest alleen Mifare Classic 1K/4K en Ultralight | € 10–15 |
| 1 | **MAX98357A I2S-versterker** (Adafruit 3006 of kloon) | Mono, 3 W aan 4 Ω | € 5–8 |
| 1 | Speaker 4 Ω, 3–5 W, Ø 66–80 mm | Bijv. Visaton FRS 8 (4 Ω-versie) of FR 7 | € 10–15 |
| 5 | Arcade-knoppen 30 mm (of 24 mm) | Play/pauze, vorige, volgende, volume −, volume + (verschillende kleuren!) | € 8 |
| 1 | LED 5 mm + weerstand 330 Ω | Statuslampje "box is klaar" | € 1 |
| 8 | Weerstand 1 kΩ | Beschermweerstand in serie per knop (aanrader, niet verplicht) | € 1 |
| 1 set | Dupont-kabels female-female 20 cm | Voor de Pi-header | € 4 |
| 1 | Stukje gaatjesprint (perfboard) | Voor een gezamenlijke GND-rail | € 2 |
| – | Montagedraad, krimpkous, soldeerbout en tin | | |
| – | Heat-set inserts M2.5 en M3 + boutjes | Voor het geprinte kastje | € 8 |
| 1 | *Optioneel:* draaiknop KY-040 | Als alternatief voor de volumeknoppen | € 2 |
| 1 | *Optioneel:* actieve buzzer (KY-012) | Piept bij kaart scannen | € 1 |
| 1 | *Optioneel:* USB-C-paneeldoorvoer (kort, 3 A) | Nette laadaansluiting in de kastwand | € 5 |

> **Waarom de MAX98357A?** De 3,5 mm-jack van de Pi 3B ruist en klinkt dun. De MAX98357A
> krijgt het geluid digitaal (I2S), heeft zelf een DAC en versterker, en stuurt de
> speaker direct aan. Hij gebruikt GPIO 18, 19 en 21.

---

## 2. Eigen Git-repository opzetten

De code staat lokaal in `Toniebox\phoniebox`:

- remote **`upstream`** = het officiële Phoniebox-project
- branch **`eigen/main`** = onze versie, met deze handleiding in de map `eigen/`

### 2.1 Op GitHub zetten

Het installatiescript downloadt de code van GitHub. Daarom gelden twee eisen:

- De repository moet **`RPi-Jukebox-RFID`** heten. Het script gaat daarvan uit.
- Hij moet **publiek** zijn. Het script downloadt zonder inloggen (`wget …/tarball/<branch>`).
  Er staan geen wachtwoorden of persoonsgegevens in, die staan alleen op de Pi zelf.

**Optie A: fork (makkelijkst om updates binnen te halen)**

1. Ga naar <https://github.com/MiczFlor/RPi-Jukebox-RFID> en klik op **Fork**.
2. Koppel de lokale map aan je fork en push onze branch:

   ```powershell
   cd <map-met-de-lokale-kopie>
   git remote add origin https://github.com/<jouw-github-naam>/RPi-Jukebox-RFID.git
   git push -u origin eigen/main
   ```

**Optie B: nieuwe, losse repository.** Maak op GitHub een lege publieke repo
`RPi-Jukebox-RFID` aan, zonder README, en voer dezelfde twee `git`-commando's uit.

### 2.2 Werkwijze

- Eigen aanpassingen gaan in `eigen/main`, of in een feature-branch die je daarin merget.
- Nieuwe officiële versies haal je zo binnen:

  ```powershell
  git fetch upstream
  git merge upstream/future3/main
  git push
  ```

- Op de Pi updaten: zie `documentation/builders/update.md`, of installeer opnieuw (hoofdstuk 5).

---

## 3. Pinplan: wat gaat waar

Bovenaanzicht van de Pi, de 40-pins header rechtsboven en de USB-poorten naar beneden.
Pin 1 is het **vierkante** soldeereilandje.

```text
                     3V3  (1) (2)  5V     ── MAX98357A VIN
  (I2C PiSugar) ─ GPIO 2  (3) (4)  5V
  (I2C PiSugar) ─ GPIO 3  (5) (6)  GND    ── MAX98357A GND
                  GPIO 4  (7) (8)  GPIO14
                     GND  (9) (10) GPIO15
     status-LED ── GPIO17 (11) (12) GPIO18 ── MAX98357A BCLK
   (opt.) buzzer ─ GPIO27 (13) (14) GND    ── GND-rail knoppen
    volume − ──── GPIO22 (15) (16) GPIO23 ── volume +
   RC522 3.3V ──     3V3 (17) (18) GPIO24 ── RC522 IRQ
   RC522 MOSI ── GPIO10 (19) (20) GND    ── RC522 GND
   RC522 MISO ──  GPIO9 (21) (22) GPIO25 ── RC522 RST
    RC522 SCK ── GPIO11 (23) (24) GPIO8  ── RC522 SDA
  status-LED − ──    GND (25) (26) GPIO7
                   ID_SD (27) (28) ID_SC
 (opt.) KY-040 CLK GPIO5 (29) (30) GND    ── (opt.) KY-040 GND
 (opt.) KY-040 DT  GPIO6 (31) (32) GPIO12 ── (opt.) KY-040 SW
    play/pauze ── GPIO13 (33) (34) GND
MAX98357A LRC ── GPIO19 (35) (36) GPIO16 ── vorige
      volgende ── GPIO26 (37) (38) GPIO20    (vrij laten, I2S)
                     GND (39) (40) GPIO21 ── MAX98357A DIN
```

### Overzichtstabel

| Onderdeel | Pin onderdeel | Fysieke Pi-pin | GPIO (BCM) |
|---|---|---|---|
| **RC522** | 3.3V | 17 | – |
| | GND | 20 | – |
| | SDA | 24 | GPIO 8 (CE0) |
| | SCK | 23 | GPIO 11 |
| | MOSI | 19 | GPIO 10 |
| | MISO | 21 | GPIO 9 |
| | IRQ | 18 | GPIO 24 |
| | RST | 22 | GPIO 25 |
| **MAX98357A** | VIN | 2 (5 V) | – |
| | GND | 6 | – |
| | BCLK | 12 | GPIO 18 |
| | LRC | 35 | GPIO 19 |
| | DIN | 40 | GPIO 21 |
| | GAIN, SD | niet aansluiten | – |
| | Speaker + / − | schroefklemmen op het bordje | – |
| **PiSugar 3 Plus** | pogo pins aan de onderkant | (5 V, GND, 3, 5) | GPIO 2/3 (I2C), **niet bedraden** |
| **Play/pauze** | NO / COM | 33 / GND-rail | GPIO 13 |
| **Vorige** | NO / COM | 36 / GND-rail | GPIO 16 |
| **Volgende** | NO / COM | 37 / GND-rail | GPIO 26 |
| **Volume −** | NO / COM | 15 / GND-rail | GPIO 22 |
| **Volume +** | NO / COM | 16 / GND-rail | GPIO 23 |
| **Status-LED** | + (lange poot) via 330 Ω | 11 | GPIO 17 |
| | − (korte poot) | 25 | – |
| *Opt. KY-040* | + / GND | 1 (**3,3 V!**) / 30 | – |
| | CLK / DT / SW | 29 / 31 / 32 | GPIO 5 / 6 / 12 |
| *Opt. buzzer* | + / − | 13 / GND | GPIO 27 |

Deze pinnen zijn bewust zo gekozen:

- **GPIO 2 en 3** (I2C) zijn voor de PiSugar-accu, die daarover het batterijniveau doorgeeft.
  Aan/uit gaat met de knop van de PiSugar. Zonder accu kun je een aan/uit-knop op GPIO 3 zetten
  (zie het commentaar in `eigen/gpio.yaml`).
- **GPIO 18, 19, 20, 21** zijn van de I2S-versterker. De voorbeeldconfig van Phoniebox
  gebruikt GPIO 18 voor een LED. Dat botst met de versterker en moet je niet overnemen.
- De knoppen gebruiken de **interne pull-up** van de Pi, dus er zijn geen extra weerstanden
  naar 3,3 V nodig. De knop verbindt de GPIO met GND.

---

## 4. Aansluiten, stap voor stap

> ⚠️ **Altijd stroom eraf bij het aansluiten.** Een verkeerde draad op 5 V kan een GPIO-pin
> (of de hele Pi) slopen. **De GPIO's en de RC522 kunnen maximaal 3,3 V hebben.**

Bouw alles eerst **los op tafel** en test het (hoofdstuk 6). Pas daarna gaat het in het kastje.

### 4.1 Solderen van de modules

1. **RC522:** soldeer de rechte pinheader erop. Of soldeer de draden direct, dat is plat en
   handig onder het deksel.
2. **MAX98357A:** soldeer de header en de schroefklem voor de speaker.
3. **Speaker:** soldeer twee draden (± 15 cm) aan de speaker en zet ze in de schroefklem.
   De polariteit maakt bij één speaker niet uit.

### 4.2 GND-rail

De Pi heeft maar 8 GND-pinnen. Maak daarom een **GND-rail** voor de knoppen:

1. Neem een strookje gaatjesprint en soldeer een rij van ± 8 punten met tin of een kaal draadje aan elkaar.
2. Verbind de rail met één draad met **pin 14 (GND)**.
3. Sluit alle COM-contacten van de knoppen aan op de rail.

### 4.3 Arcade-knoppen

Een arcade-knop heeft een microswitch met 3 lipjes: **COM**, **NO** (normally open) en
**NC** (normally closed). Gebruik **COM** en **NO**. NC blijft leeg.

```text
 Pi GPIO-pin ──[ 1 kΩ ]── NO  ┐
                              ├─ microswitch
 GND-rail ─────────────── COM ┘
```

De 1 kΩ-weerstand is optioneel. Hij beschermt de pin als je per ongeluk een pin als uitgang
configureert. Krimpkous eroverheen.

Doe dit voor: play/pauze (pin 33), vorige (36), volgende (37), volume − (15) en volume + (16).

**Kleuradvies voor kleine kinderen:** groot groen = play/pauze in het midden, blauw links/rechts
= vorige/volgende, geel/rood = volume −/+. Plak eventueel een symbooltje op de knop.

### 4.4 Accu (PiSugar 3 Plus)

Schroef de PiSugar onder de Pi. De pogo pins maken zelf contact, dus er zijn geen draden nodig.
Aan/uit gaat met de knop op de PiSugar. Alles over montage, software en het kastje staat in [ACCU.md](ACCU.md).

### 4.5 Status-LED

```text
 pin 11 (GPIO 17) ──[ 330 Ω ]──►|── pin 25 (GND)
                         lange poot  korte poot
```

### 4.6 RC522-lezer

Sluit hem aan volgens de tabel in hoofdstuk 3 (8 draden). Twee aandachtspunten:

- **3.3V naar pin 17, niet naar 5 V.**
- Leest hij geen kaarten? Op sommige bordjes zijn MOSI en MISO verkeerd om gelabeld.
  Wissel die twee draden om. Dat kan geen kwaad.

### 4.7 MAX98357A-versterker

Sluit 5 draden aan: VIN→2, GND→6, BCLK→12, LRC→35, DIN→40. Laat **GAIN** los (9 dB) en
laat **SD** los (mono-mix van links en rechts). Het maximale volume begrenzen we in de software.

### 4.8 (Optioneel) KY-040 draaiknop

Gebruik je deze in plaats van de volumeknoppen, sluit hem dan aan volgens de tabel. Zet daarbij
**+ op 3,3 V (pin 1)**, want het bordje heeft eigen pull-ups en op 5 V komt er 5 V op de GPIO.
Het mag ook allebei: draaiknop én knoppen.

### 4.9 Stroom

De PiSugar levert de 5 V aan de Pi (tot 3 A). De versterker haalt zijn stroom uit de Pi (pin 2).
Laden gaat **alleen via de USB-C van de PiSugar**. Steek nooit tegelijk een voeding in de
micro-USB van de Pi. Komt er de melding "under-voltage" in de log, kijk dan of de accu bijna leeg is
of gebruik een betere USB-C-lader.

---

## 5. Software installeren

### 5.1 SD-kaart voorbereiden

1. Installeer de [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Kies bij Model "No filtering". Kies bij OS **Raspberry Pi OS (other) → Raspberry Pi OS (Legacy, 32-bit) Lite**.
   Phoniebox raadt de *Legacy Lite* aan.
3. Stel bij Customize in:
   - Hostname: `muziekbox`
   - Gebruiker + wachtwoord: kies zelf
   - Wifi: jullie netwerk
   - Land/tijdzone: NL / Europe/Amsterdam
   - SSH aan, met wachtwoord
4. Klik op Write, stop de kaart in de Pi en sluit de stroom aan. Wacht ± 2 minuten.

### 5.2 Inloggen

Gebruik in PowerShell op je pc:

```powershell
ssh <gebruiker>@muziekbox.local
```

Werkt `muziekbox.local` niet, zoek dan het IP-adres op in je router.

### 5.3 Phoniebox installeren vanaf onze eigen GitHub

Start eerst een `tmux`-sessie, zodat de installatie doorloopt als je SSH-verbinding wegvalt:

```bash
sudo apt install -y tmux && tmux
```

Installeer daarna. Vervang `<jouw-github-naam>`:

```bash
cd; GIT_USER='<jouw-github-naam>' GIT_BRANCH='eigen/main' bash <(wget -qO- https://raw.githubusercontent.com/<jouw-github-naam>/RPi-Jukebox-RFID/eigen/main/installation/install-jukebox.sh)
```

Beantwoord de vragen van het script zo:

| Vraag | Antwoord |
|---|---|
| Disable IPv6? | `Y` (standaard) |
| Autohotspot? | `N`. Kan handig zijn als de box buiten bereik van de wifi gebruikt wordt |
| Disable Bluetooth? | `Y`, tenzij je een bluetooth-koptelefoon wilt gebruiken |
| Setup a rfid reader? | `Y` → kies **RC522 SPI**, laat alle pinnen op de standaardwaarden |
| Install Samba? | `Y`. Handig om instellingen en logs te bekijken via `\\muziekbox\phoniebox` |
| Install the Web App? | `Y` |
| Kiosk Mode? | `N` |
| Update the operating system? | `Y` |
| Build the Web App? | `Y`. Dat is nodig omdat we vanaf een fork installeren |

> ⏱ **Duur:** op een Pi 3B ruim een uur, vooral door het bouwen van de webapp.
> Het script vergroot het swapgeheugen zelf. Volg de voortgang in een tweede SSH-venster
> met `tail -f ~/INSTALL-*.log`. Faalt de webapp-build met "heap out of memory", draai dan
> achteraf `cd ~/RPi-Jukebox-RFID/src/webapp && ./run_rebuild.sh -u`.

Herstart na afloop: `sudo reboot`.

### 5.4 Geluid via de MAX98357A inschakelen

De MAX98357A werkt met de "hifiberry-dac"-driver:

```bash
cd ~/RPi-Jukebox-RFID/installation/components
./setup_hifiberry.sh enable hifiberry-dac
sudo reboot
```

Daarna testen en de Phoniebox-audioconfig draaien:

```bash
pactl list sinks short          # er moet een "snd_rpi_hifiberry_dac"-achtige sink staan
paplay /usr/share/sounds/alsa/Front_Center.wav
cd ~/RPi-Jukebox-RFID/installation/components && ./setup_configure_audio.sh
```

Hoor je niets? Zie hoofdstuk 9.

---

## 6. Configureren en testen

Alle instellingen staan in `~/RPi-Jukebox-RFID/shared/settings/`. Werk altijd zo:

```bash
systemctl --user stop jukebox-daemon      # stoppen
nano ~/RPi-Jukebox-RFID/shared/settings/jukebox.yaml
systemctl --user start jukebox-daemon     # starten
```

### 6.1 Knoppen en LED (gpio.yaml)

Kopieer onze knoppenconfig uit de repo:

```bash
systemctl --user stop jukebox-daemon
cp ~/RPi-Jukebox-RFID/eigen/gpio.yaml ~/RPi-Jukebox-RFID/shared/settings/gpio.yaml
```

Zet in `shared/settings/jukebox.yaml` de GPIO-module aan:

```yaml
gpioz:
  enable: true
  config_file: ../../shared/settings/gpio.yaml
```

### 6.2 Volume kindvriendelijk maken

In `jukebox.yaml`, onder `pulse:`:

```yaml
  startup_volume: 30       # volume na opstarten
  soft_max_volume: 60      # kinderen komen nooit boven 60 %
```

Start de daemon weer. Het maximum kun je ook in de webapp aanpassen.

### 6.3 Testen per onderdeel

Open de log in een apart venster: `tail -f ~/RPi-Jukebox-RFID/shared/logs/app.log`.
Via de browser kan ook: `http://muziekbox.local/logs`.

| Test | Verwacht |
|---|---|
| Webapp openen: `http://muziekbox.local` | Phoniebox-interface |
| Status-LED | Gaat aan zodra de box opgestart is |
| Kaart tegen de lezer | Kaart-ID verschijnt in de log en in de webapp (Cards → Register) |
| Elke knop indrukken | Regel in de log met de actie (`toggle`, `next_song`, …) |
| PiSugar-knop lang indrukken | Pi sluit af en de stroom gaat eraf. Kort drukken = weer aan |
| Instellingen → Status in de webapp | Batterijpercentage, en "charging" als de lader erin zit |

### 6.4 Kaarten koppelen

Kaarten koppel je vooral aan **Spotify-playlists**, zie [SPOTIFY.md](SPOTIFY.md). Print voor
elke kaart een plaatje van de playlist en plak het erop.

Lokale MP3's kunnen ook, als iets niet op Spotify staat. Zet ze via `\\muziekbox\phoniebox`
in een map onder `audiofolders` en kies bij de kaart **Play music**.

**Tip:** maak ook een paar "functiekaarten", bijvoorbeeld een slaaptimer van 15 min of het
volume op 20 %. Ook die stel je in via Cards.

---

## 7. Kastje printen met de Prusa

### 7.1 Indeling (voorstel)

Buitenmaat ongeveer **170 × 130 × 110 mm** (b × d × h). Dat past op het bed van een MK3/MK4/Core One.

```text
   Bovenaanzicht (deksel)               Vooraanzicht
 ┌──────────────────────────┐        ┌──────────────────────────┐
 │  ┌────────────────┐      │        │  ░░░░░░░░░░░░░░░░░░░░    │
 │  │  NFC-vlak      │  ●   │ LED    │  ░ speakerrooster ░░░    │
 │  │  (RC522 eronder)│      │        │  ░░░░░░░░░░░░░░░░░░░░    │
 │  └────────────────┘      │        │                          │
 │   (−)   (◄◄)  (▶‖)  (►►)  (+)│    │                          │
 └──────────────────────────┘        └──────────────────────────┘
   Achterkant: USB-C-laadingang, drukstift naar PiSugar-knop, ventilatiesleuven
```

### 7.2 Maten om in te tekenen

| Onderdeel | Gat / bevestiging |
|---|---|
| Raspberry Pi 3B (85 × 56 mm) + PiSugar 3 Plus eronder | 4× M2.5-staander, gatafstand **58 × 49 mm**, gaten 3,5 mm uit de rand. Het pakket wordt ± 15–20 mm hoger door de accu: **meet je exemplaar** |
| RC522 (± 60 × 40 mm) | Gaten verschillen per kloon, **opmeten**. Monteer hem met de antenne direct tegen de binnenkant van het deksel |
| MAX98357A (± 18 × 20 mm) | Klein vakje met klem, of dubbelzijdig tape |
| Arcade-knop 30 mm | Gat **Ø 30 mm**, wanddikte max ± 5 mm voor de moer (24 mm-knop: Ø 24 mm) |
| PiSugar-knop | Drukstift door de wand (PETG-pen met kraag of TPU-knop), zie [ACCU.md](ACCU.md) |
| LED 5 mm | Gat Ø 5,2 mm, of een LED-houder |
| KY-040 (optioneel) | Gat Ø 7 mm voor de as, plus een nokje tegen meedraaien |
| Speaker FRS 8 | Uitsparing ± Ø 72 mm, 4× M3-gat volgens het datasheet; rooster van gaatjes Ø 3–4 mm |
| USB-C (PiSugar) | Opening bij de poort of een USB-C-paneeldoorvoer; laat ± 15 mm ruimte voor de stekker |
| Accu | Eigen vak met ± 2 mm speling, geen schroeven of scherpe randen ertegen |

### 7.3 Printtips

- **Deksel boven de RC522: maximaal 2 mm dik** op het NFC-vlak. Dikker gaat ook nog,
  maar dan wordt het leesbereik merkbaar kleiner. Gebruik **geen metaal** en geen
  metallic- of carbon-gevuld filament in de buurt van de antenne. Maak een verdiept vlak
  van 1 mm waar de kaart in "valt", met een icoontje, zodat kinderen zien waar hij moet.
- **Materiaal:** PETG (taaier, kan beter tegen een val) of PLA. 3 perimeters, 20–25 % gyroid.
- **Wand 2,4–3 mm**, ronde hoeken (fillet ≥ 3 mm), dat is kindvriendelijk.
- **Heat-set inserts** (M2.5 voor de Pi, M3 voor deksel en speaker) zijn veel sterker dan
  schroeven in plastic. Gebruik boutjes die de kinderen niet makkelijk los krijgen (inbus/torx).
- **Speaker:** monteer hem tegen de voorwand met een ring foam of TPU als afdichting.
  Een **gesloten speakerkamer** (binnenwandje rond de speaker) geeft merkbaar meer bas.
- **Ventilatie:** de Pi 3B wordt warm. Maak sleuven onderin en bovenin de achterwand.
- **Ruimte voor kabels:** de Dupont-stekkers op de header steken ± 15 mm uit. Houd boven
  de Pi minstens 25 mm vrij, of gebruik haakse Dupont-connectors.
- **Kijk ter inspiratie op Printables:** zoek op "Phoniebox" of "jukebox rfid". Daar staan
  bestaande ontwerpen die je kunt aanpassen.

---

## 8. Spotify

De box draait vooral op Spotify: een kaart start een gedeelde playlist. Alles over het
aanmaken van de Spotify-app, installeren, kaarten koppelen en problemen oplossen staat in
**[SPOTIFY.md](SPOTIFY.md)**.

Kort samengevat, nadat hoofdstuk 5 en 6 klaar zijn:

```bash
cd ~/RPi-Jukebox-RFID/installation/components && ./setup_spotify.sh
systemctl --user restart jukebox-daemon
```

Daarna kies je in de webapp bij een kaart de actie **Spotify**.

---

## 9. Problemen oplossen

| Probleem | Oplossing |
|---|---|
| Kaart wordt niet gelezen | 3,3 V en GND controleren, MOSI/MISO omwisselen, is het een **Mifare Classic**-kaart (geen NTAG)? Staat er metaal in de buurt of is het deksel te dik? |
| Geen geluid | `cat /boot/firmware/config.txt` (of `/boot/config.txt`) moet `dtoverlay=hifiberry-dac` bevatten; `pactl list sinks short` checken; draden BCLK/LRC/DIN controleren (pin 12/35/40) |
| Geluid kraakt bij hoog volume | `soft_max_volume` lager zetten, of een betere voeding |
| Knop doet niets | Staat `gpioz: enable: true`? Pinnummer in `gpio.yaml` is het **GPIO**-nummer, niet het fysieke pinnummer. Zit de draad op NO en niet op NC? |
| Knop reageert dubbel | `bounce_time: 0.1` toevoegen onder `kwargs` van die knop |
| Box start niet / start steeds opnieuw op | Accu leeg: laad hem via USB-C. Gebeurt het tijdens het laden, gebruik dan een 3 A-lader |
| Geen batterijniveau in de webapp | Draait `pisugar-server` (`systemctl status pisugar-server`)? Staat I2C aan? Zie [ACCU.md](ACCU.md) |
| Webapp niet bereikbaar | `systemctl --user status jukebox-daemon` en `sudo systemctl status nginx` |
| Log bekijken | `~/RPi-Jukebox-RFID/shared/logs/app.log` en `errors.log`, of `http://muziekbox.local/logs` |

Meer informatie staat in `documentation/builders/` in deze repo.
