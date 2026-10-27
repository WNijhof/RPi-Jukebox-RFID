# Accu: de muziekbox oplaadbaar maken

## Keuze: PiSugar 3 Plus

| | PiSugar 3 Plus |
|---|---|
| Wat is het | Accu (5000 mAh) met laad- en power-elektronica, voor Pi 3B/3B+/4B |
| Montage | Wordt **onder** de Pi geschroefd. Veerpennen (pogo pins) maken contact met de onderkant van de Pi, dus **geen draden** en alle GPIO-pinnen blijven vrij |
| Laden | Via **USB-C**, ook terwijl de box speelt (UPS-functie: de box schakelt niet uit als je de stekker erin of eruit haalt) |
| Aan/uit | Eigen knop: aanzetten, en lang drukken = netjes afsluiten waarna de stroom er **helemaal** af gaat. Een uitgezette box loopt dus niet leeg |
| Uitlezen | Batterij-percentage via I2C. Het staat in de webapp van de box (Instellingen → Status) en in de PiSugar-webpagina |
| Te koop | **Tinytronics** (Eindhoven, op voorraad): € 51. Op AliExpress is hij duurder (€ 72–78) |
| Maat / gewicht | 65 × 56 mm, 96 g, M2.5-montage |

**Speelduur (schatting):** 5000 mAh × 3,7 V ≈ 18,5 Wh. Na verliezen blijft ± 15 Wh over. De Pi 3B
met wifi, Spotify en de versterker op gemiddeld volume gebruikt ± 2,5 W. Dat geeft **ongeveer 5–6 uur
luisteren** per lading. Harder volume = korter.

### Waarom niet ...

| Alternatief | Nadeel voor deze box |
|---|---|
| Gewone powerbank | Veel powerbanks schakelen uit bij laag verbruik of onderbreken kort bij het inpluggen van de lader, en dan herstart de Pi. Je ziet ook geen batterijniveau. Kan wel als goedkope tussenoplossing: kies er een met "pass-through charging" |
| Waveshare UPS HAT (A), 2× 18650 | Langere speelduur (± 8–10 uur), maar laden gaat via een 8,4 V-adapter met ronde plug, hij zit bovenop de GPIO-header en de aan/uit-schakelaar zit op het bordje |
| Geekworm X728 | Gebruikt GPIO 5, 6, 12 en 13. Die pinnen hebben wij al voor de knoppen |
| Zelf 18650-cellen + laadmodule | Niet doen in kinderspeelgoed: het risico zit in de beveiliging (BMS) en die is bij kant-en-klare modules beter geregeld |

## Boodschappen

| Onderdeel | Ca. prijs |
|---|---|
| PiSugar 3 Plus (Tinytronics) | € 51 |
| USB-C-lader 5 V / 3 A (bijv. officiële Raspberry Pi USB-C-voeding) | € 10 |
| *Optioneel:* USB-C-paneeldoorvoer (female–male, kort, geschikt voor 3 A) | € 5 |

De micro-USB-voeding van de Pi en de aparte aan/uit-arcadeknop uit de boodschappenlijst zijn
dan **niet meer nodig**.

## Aansluiten

1. **Stroom eraf** en de Pi uit de kast.
2. Schroef de PiSugar met de meegeleverde afstandsbusjes onder de Pi. De pogo pins moeten precies
   op de koperen eilandjes aan de onderkant van de Pi drukken (5V, GND en I2C).
3. Sluit **niets** aan op de micro-USB van de Pi. Je laadt alleen via de USB-C van de PiSugar.
   Twee voedingen tegelijk is vragen om problemen.
4. De versterker blijft gewoon op pin 2 (5 V) van de Pi. Die 5 V komt nu van de PiSugar.
5. **De aan/uit-knop op GPIO 3 vervalt.** GPIO 2 en 3 zijn de I2C-pinnen waarmee de Pi het
   batterijniveau uitleest. In `eigen/gpio.yaml` staat die knop daarom uitgecommentarieerd.

Pinplan na deze wijziging:

| Pin | Was | Wordt |
|---|---|---|
| 3 (GPIO 2) en 5 (GPIO 3) | 5 = aan/uit-knop | **I2C voor de PiSugar** (via de onderkant, niet bedraden) |
| 9 (GND) | GND aan/uit-knop | vrij |
| alle andere | ongewijzigd | ongewijzigd |

## Software

### PiSugar Power Manager installeren

Volg de actuele installatie-instructie op
<https://github.com/PiSugar/pisugar-power-manager-rs>. Bij het schrijven van deze handleiding kwam die neer op:

```bash
curl https://cdn.pisugar.com/release/pisugar-power-manager.sh | sudo bash
```

- Kies tijdens de installatie het model **PiSugar 3**.
- I2C moet aan staan. Doet het script dat niet zelf, gebruik dan `sudo raspi-config` → *Interface Options* → *I2C* → *Yes*.
- Daarna draait `pisugar-server` en is de PiSugar-webpagina bereikbaar op
  `http://muziekbox.local:8421`.

### Instellingen in de PiSugar-webpagina

| Instelling | Advies |
|---|---|
| Knop: *long press* | Afsluiten (`sudo shutdown -h now`) |
| *Soft poweroff* / stroom eraf na afsluiten | Aan, zodat de box na het afsluiten echt niets meer verbruikt |
| *Safe shutdown* bij laag batterijniveau | Bijv. 5 %. De box heeft zelf ook een grens (zie hieronder); de laagste wint |
| *Anti-mistouch* | Aan, zodat de kinderen de box niet per ongeluk uitzetten |

De namen van deze instellingen kunnen per softwareversie verschillen. Kijk bij twijfel in de PiSugar-documentatie.

### Batterijniveau in de box-software

In onze fork staat de batterijmodule al aan (`resources/default-settings/jukebox.default.yaml`):

```yaml
modules:
  named:
    battmon: battery_monitor.batt_mon_pisugar
battmon:
  warning_level: 10      # onder 10 %: warning_action één keer uitvoeren
  warning_action:        # bijv. volume omlaag:  {alias: set_volume, args: 20}
  shutdown_level: 3      # onder 3 %: netjes afsluiten
```

Heb je de box geïnstalleerd vóórdat deze module erin zat? Voeg die regels dan zelf toe aan
`shared/settings/jukebox.yaml` en herstart: `systemctl --user restart jukebox-daemon`.

Het batterijniveau staat daarna in de webapp onder **Instellingen → Status**.

## Kastje aanpassen (Prusa)

- **Hoogte:** de PiSugar 3 Plus met accu maakt het pakket onder de Pi ± 15–20 mm hoger.
  **Meet je exemplaar** voordat je de staanders tekent.
- **USB-C:** maak een opening precies bij de USB-C-poort van de PiSugar, of gebruik een korte
  USB-C-paneeldoorvoer in de achterwand. Dat is netter en spaart de poort.
- **Knop:** de knop zit op de PiSugar zelf. Print een **drukstift** die door de kastwand naar de
  knop loopt, bijvoorbeeld een PETG-pen met een kraagje, of een flexibele TPU-knop in de wand.
  Plaats hem aan de achterkant of onderkant, zodat de kinderen hem niet per ongeluk indrukken.
- **Accu beschermen:** geen schroeven of scherpe randen tegen de accu. Laat ± 2 mm ruimte rondom
  (accu's zetten iets uit bij warmte) en zorg dat de accu niet tegen de warmste plek van de Pi ligt.
- **Ventilatie:** sleuven onder- en bovenin, zeker omdat er nu ook geladen wordt.
- **Materiaal:** PETG kan beter tegen warmte dan PLA. Dat is fijn bij laden in de zon of op de vensterbank.

## Gebruik

| Actie | Hoe |
|---|---|
| Aanzetten | Knop van de PiSugar kort indrukken |
| Uitzetten | Knop lang indrukken: de box sluit netjes af en schakelt de stroom uit |
| Opladen | USB-C-lader erin. Spelen tijdens het laden mag |
| Batterij leeg | Onder 10 % voert de box de waarschuwingsactie uit (als ingesteld), onder 3 % sluit hij netjes af |

## Veiligheid

- Laad de eerste keren **onder toezicht** en voel of de box niet warm wordt.
- Laad niet onder een deken of kussen, of in de felle zon.
- Een **opgezwollen of beschadigde accu** gebruik je niet meer en lever je in bij een inzamelpunt.
- Sluit het accuvak af met boutjes die de kinderen niet los krijgen.
