"""Aansluitschema's voor de handleiding (PNG). Gebruik: python diagrams.py <uitvoermap>"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402

plt.rcParams['font.family'] = 'Arial'

C = {'rc522': '#1565c0', 'amp': '#c1121f', 'btn': '#2a9d8f', 'led': '#38b000', 'i2c': '#8d6e63',
     '5v': '#e63946', '3v3': '#f4a261', 'gnd': '#222222', 'free': '#d9d9d9'}

# fysieke pin -> (naam op de Pi, functie in de box, groep)
PINS = {
    1: ('3V3', '', '3v3'), 2: ('5V', 'MAX98357 VIN', '5v'),
    3: ('GPIO 2', 'I2C PiSugar (pogo)', 'i2c'), 4: ('5V', '', '5v'),
    5: ('GPIO 3', 'I2C PiSugar (pogo)', 'i2c'), 6: ('GND', 'MAX98357 GND', 'gnd'),
    7: ('GPIO 4', '', 'free'), 8: ('GPIO 14', '', 'free'),
    9: ('GND', '', 'gnd'), 10: ('GPIO 15', '', 'free'),
    11: ('GPIO 17', 'status-LED +', 'led'), 12: ('GPIO 18', 'MAX98357 BCLK', 'amp'),
    13: ('GPIO 27', '(opt. buzzer)', 'free'), 14: ('GND', 'GND-rail knoppen', 'gnd'),
    15: ('GPIO 22', 'knop volume -', 'btn'), 16: ('GPIO 23', 'knop volume +', 'btn'),
    17: ('3V3', 'RC522 3.3V', '3v3'), 18: ('GPIO 24', 'RC522 IRQ', 'rc522'),
    19: ('GPIO 10', 'RC522 MOSI', 'rc522'), 20: ('GND', 'RC522 GND', 'gnd'),
    21: ('GPIO 9', 'RC522 MISO', 'rc522'), 22: ('GPIO 25', 'RC522 RST', 'rc522'),
    23: ('GPIO 11', 'RC522 SCK', 'rc522'), 24: ('GPIO 8', 'RC522 SDA', 'rc522'),
    25: ('GND', 'status-LED -', 'gnd'), 26: ('GPIO 7', '', 'free'),
    27: ('ID_SD', '', 'free'), 28: ('ID_SC', '', 'free'),
    29: ('GPIO 5', '', 'free'), 30: ('GND', '', 'gnd'),
    31: ('GPIO 6', '', 'free'), 32: ('GPIO 12', '', 'free'),
    33: ('GPIO 13', 'knop play/pauze', 'btn'), 34: ('GND', '', 'gnd'),
    35: ('GPIO 19', 'MAX98357 LRC', 'amp'), 36: ('GPIO 16', 'knop vorige', 'btn'),
    37: ('GPIO 26', 'knop volgende', 'btn'), 38: ('GPIO 20', '(vrij laten, I2S)', 'free'),
    39: ('GND', '', 'gnd'), 40: ('GPIO 21', 'MAX98357 DIN', 'amp'),
}


def pinout(path):
    fig, ax = plt.subplots(figsize=(10, 11), dpi=150)
    ax.set_xlim(-6, 6)
    ax.set_ylim(-21.6, 2.0)
    ax.axis('off')
    ax.add_patch(FancyBboxPatch((-0.9, -19.6), 1.8, 20.0, boxstyle='round,pad=0.1', fc='#1b1b1b', ec='none'))
    for p, (name, func, grp) in PINS.items():
        row = (p - 1) // 2
        left = p % 2 == 1
        x = -0.4 if left else 0.4
        y = -row
        ax.add_patch(Circle((x, y), 0.3, fc=C[grp], ec='white', lw=1.2))
        ax.text(x, y, str(p), color='white' if grp not in ('free', '3v3') else 'black', ha='center', va='center',
                fontsize=7, fontweight='bold')
        tx = -1.1 if left else 1.1
        ha = 'right' if left else 'left'
        ax.text(tx, y, name, ha=ha, va='center', fontsize=9, color='#333')
        if func:
            fx = -2.4 if left else 2.4
            ax.text(fx, y, func, ha=ha, va='center', fontsize=10, color=C[grp] if grp != 'free' else '#777',
                    fontweight='bold' if grp not in ('free',) else 'normal')
    ax.text(0, 1.55, 'Raspberry Pi 3B - 40-pins header (pin 1 = vierkant eilandje)', ha='center', fontsize=13,
            fontweight='bold')
    ax.text(0, 1.0, 'bovenaanzicht, USB-poorten naar beneden', ha='center', fontsize=9, color='#555')
    legend = [('RC522', 'rc522'), ('MAX98357', 'amp'), ('Knoppen', 'btn'), ('LED', 'led'), ('PiSugar I2C', 'i2c'),
              ('5V', '5v'), ('3,3V', '3v3'), ('GND', 'gnd')]
    for i, (lbl, g) in enumerate(legend):
        xx = -5.9 + i * 1.6
        ax.add_patch(Circle((xx, -21.1), 0.2, fc=C[g], ec='none'))
        ax.text(xx + 0.3, -21.1, lbl, va='center', fontsize=8.5)
    fig.savefig(path, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def connection(path, title, comp, comp_pins, color, note=None, extra=None):
    """Onderdeel links met pinnen, Pi-header rechts, gekleurde draden ertussen"""
    n = len(comp_pins)
    fig, ax = plt.subplots(figsize=(9, 0.62 * n + 1.8), dpi=150)
    ax.set_xlim(0, 10)
    ax.set_ylim(-n - 0.8, 2.0)
    ax.axis('off')
    ax.add_patch(FancyBboxPatch((0.3, -n + 0.1), 2.6, n - 0.2 + 0.6, boxstyle='round,pad=0.1', fc=color, ec='none',
                                alpha=0.9))
    ax.text(1.6, 0.85, comp, ha='center', fontsize=12, fontweight='bold', color=color)
    ax.add_patch(FancyBboxPatch((7.1, -n + 0.1), 2.6, n - 0.2 + 0.6, boxstyle='round,pad=0.1', fc='#1b1b1b',
                                ec='none'))
    ax.text(8.4, 0.85, 'Raspberry Pi', ha='center', fontsize=12, fontweight='bold')
    # Signaaldraden: geen rood/zwart/oranje, die zijn voor 5V/GND/3,3V
    wire_cols = ['#2a9d8f', '#8338ec', '#3a86ff', '#ffbe0b', '#ff006e', '#06d6a0', '#8d99ae', '#a47148']
    for i, (cp, pi, extra_label) in enumerate(comp_pins):
        y = -i
        ax.text(2.7, y, cp, ha='right', va='center', color='white', fontsize=10, fontweight='bold')
        ax.add_patch(Circle((2.95, y), 0.09, fc='white', ec='none'))
        if pi is None:
            ax.text(3.3, y, extra_label, va='center', fontsize=9.5, color='#666', style='italic')
            continue
        name = PINS[pi][0]
        wc = '#222' if name == 'GND' else ('#e63946' if name == '5V' else ('#f4a261' if name == '3V3'
                                                                            else wire_cols[i % len(wire_cols)]))
        ax.plot([3.0, 7.0], [y, y], color=wc, lw=3, solid_capstyle='round')
        if extra_label:
            ax.text(5.0, y + 0.18, extra_label, ha='center', fontsize=8.5, color='#444')
        ax.add_patch(Circle((7.05, y), 0.09, fc='white', ec='none'))
        ax.text(7.3, y, f'pin {pi}', va='center', color='white', fontsize=10, fontweight='bold')
        ax.text(9.6, y, name, ha='right', va='center', color='#bbb', fontsize=9)
    ax.text(5, 1.65, title, ha='center', fontsize=14, fontweight='bold')
    if note:
        ax.text(5, -n - 0.45, note, ha='center', fontsize=9.5, color='#a00000')
    fig.savefig(path, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def button_schema(path):
    fig, ax = plt.subplots(figsize=(9, 3.6), dpi=150)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis('off')
    ax.set_title('Eén knop aansluiten (drukknop 16 mm, 2 soldeerlippen)', fontsize=13, fontweight='bold')
    ax.add_patch(FancyBboxPatch((6.3, 0.7), 2.6, 2.6, boxstyle='round,pad=0.05', fc='#eeeeee', ec='#555'))
    ax.text(7.6, 3.05, 'drukknop (onderkant)', ha='center', fontsize=10)
    for y, lbl in ((2.5, 'lip 1'), (1.7, 'lip 2')):
        ax.add_patch(Rectangle((6.2, y - 0.08), 0.3, 0.16, fc='#d4a017', ec='none'))
        ax.text(6.65, y, lbl, va='center', fontsize=10, fontweight='bold')
    ax.text(7.6, 1.05, 'welke lip maakt niet uit', ha='center', va='center', fontsize=8.5, color='#777')
    ax.plot([0.9, 2.4], [2.5, 2.5], color='#2a9d8f', lw=3)
    ax.add_patch(Rectangle((2.4, 2.32), 1.2, 0.36, fc='#f2e3c6', ec='#8d6e63', lw=1.5))
    ax.text(3.0, 2.5, '1 kΩ', ha='center', va='center', fontsize=9)
    ax.plot([3.6, 6.2], [2.5, 2.5], color='#2a9d8f', lw=3)
    ax.plot([0.9, 6.2], [1.7, 1.7], color='#222', lw=3)
    ax.text(0.8, 2.5, 'GPIO-pin', ha='right', va='center', fontsize=10, fontweight='bold', color='#2a9d8f')
    ax.text(0.8, 1.7, 'GND-rail', ha='right', va='center', fontsize=10, fontweight='bold')
    ax.text(4.7, 0.45, 'Ingedrukt: de lippen zijn verbonden, de pin wordt laag (interne pull-up van de Pi).',
            ha='center', fontsize=9, color='#444')
    fig.savefig(path, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def gnd_rail(path):
    fig, ax = plt.subplots(figsize=(9, 3.8), dpi=150)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis('off')
    ax.set_title('GND-rail op een strookje gaatjesprint', fontsize=13, fontweight='bold')
    ax.add_patch(Rectangle((1.5, 1.6), 6.5, 0.8, fc='#2e7d32', ec='#1b5e20'))
    for i in range(14):
        ax.add_patch(Circle((1.8 + i * 0.47, 2.0), 0.09, fc='#d4a017', ec='none'))
    ax.plot([1.8, 1.8 + 13 * 0.47], [2.0, 2.0], color='#c0c0c0', lw=3)
    ax.text(4.75, 2.65, 'soldeer de eilandjes met tin of een kaal draadje aan elkaar', ha='center', fontsize=9)
    ax.plot([1.8, 0.6], [2.0, 2.0], color='#222', lw=3)
    ax.text(0.5, 2.0, 'Pi pin 14\n(GND)', ha='right', va='center', fontsize=9.5, fontweight='bold')
    labels = ['play/pauze', 'vorige', 'volgende', 'volume -', 'volume +']
    for i, lbl in enumerate(labels):
        x = 2.8 + i * 1.1
        ax.plot([x, x], [2.0, 0.8], color='#222', lw=2.5)
        ax.text(x, 0.6, f'lip 2\n{lbl}', ha='center', va='top', fontsize=8.5)
    fig.savefig(path, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def led_schema(path):
    fig, ax = plt.subplots(figsize=(9, 2.2), dpi=150)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2.2)
    ax.axis('off')
    ax.set_title('Status-LED', fontsize=13, fontweight='bold')
    ax.plot([1.2, 3.2], [1, 1], color='#38b000', lw=3)
    ax.add_patch(Rectangle((3.2, 0.82), 1.2, 0.36, fc='#f2e3c6', ec='#8d6e63', lw=1.5))
    ax.text(3.8, 1, '330 Ω', ha='center', va='center', fontsize=9)
    ax.plot([4.4, 5.6], [1, 1], color='#38b000', lw=3)
    ax.fill([5.6, 5.6, 6.3], [0.7, 1.3, 1.0], color='#38b000')
    ax.plot([6.3, 6.3], [0.7, 1.3], color='#222', lw=3)
    ax.plot([6.3, 8.6], [1, 1], color='#222', lw=3)
    ax.text(1.1, 1, 'pin 11\n(GPIO 17)', ha='right', va='center', fontsize=9.5, fontweight='bold')
    ax.text(8.7, 1, 'pin 25\n(GND)', ha='left', va='center', fontsize=9.5, fontweight='bold')
    ax.text(5.6, 1.5, 'lange poot (+)', ha='center', fontsize=8.5)
    ax.text(6.4, 0.45, 'korte poot (-)', ha='center', fontsize=8.5)
    fig.savefig(path, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def stack(path):
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=150)
    ax.set_xlim(0, 12)
    ax.set_ylim(-0.5, 11.5)
    ax.axis('off')
    ax.set_title('Zijaanzicht: hoe alles op elkaar zit (niet op schaal)', fontsize=13, fontweight='bold')
    box = '#e9c46a'
    ax.add_patch(Rectangle((0.5, 0), 11, 0.4, fc=box, ec='#8a6d1f'))           # bodem
    ax.add_patch(Rectangle((0.5, 10.4), 11, 0.4, fc='#f1d58a', ec='#8a6d1f'))  # deksel
    for x in (3.0, 8.5):
        ax.add_patch(Rectangle((x, 0.4), 0.5, 1.0, fc=box, ec='#8a6d1f'))
    ax.text(9.2, 0.9, 'accu op foamtape, tussen hoekgeleiders', fontsize=8.5, va='center')
    ax.add_patch(Rectangle((2.6, 1.4), 6.2, 1.6, fc='#222', ec='none'))
    ax.text(5.7, 2.2, 'PiSugar 3 Plus (accu)', color='white', ha='center', va='center', fontsize=10)
    for x in (3.5, 4.0, 4.5):
        ax.add_patch(Rectangle((x, 3.0), 0.12, 0.35, fc='#d4a017', ec='none'))
    ax.text(2.4, 3.2, 'pogo pins', ha='right', fontsize=8.5, va='center')
    ax.add_patch(Rectangle((2.3, 3.35), 7.5, 0.25, fc='#2a9d4b', ec='none'))
    ax.text(10.0, 3.47, 'Raspberry Pi 3B', fontsize=9.5, va='center')
    ax.add_patch(Rectangle((4.0, 3.6), 4.5, 0.6, fc='#111', ec='none'))
    ax.text(6.25, 3.9, 'GPIO-header', color='white', ha='center', va='center', fontsize=8)
    for i, x in enumerate((4.3, 5.0, 5.7, 6.4, 7.1, 7.8)):
        ax.plot([x, x, x + 0.4 * (i - 2)], [4.2, 5.4, 6.8], color=['#1565c0', '#c1121f', '#2a9d8f'][i % 3], lw=2)
    ax.text(8.6, 5.3, 'Dupont-draden', fontsize=8.5)
    ax.add_patch(Rectangle((1.0, 10.1), 4.0, 0.3, fc='#1565c0', ec='none'))
    ax.text(3.0, 9.7, 'RC522 tegen het deksel geplakt', ha='center', fontsize=8.5)
    ax.text(3.0, 11.1, 'NFC-vlak (deksel hier 1,8 mm)', ha='center', fontsize=8.5)
    ax.add_patch(Rectangle((7.7, 10.8), 1.4, 0.45, fc='#2a9d4b', ec='none'))
    ax.add_patch(Rectangle((7.95, 7.6), 0.9, 2.8, fc='#444', ec='none'))
    ax.text(9.2, 9.0, 'drukknop 16 mm', fontsize=8.5)
    ax.annotate('', xy=(10.9, 10.4), xytext=(10.9, 0.4), arrowprops=dict(arrowstyle='<->', color='#555'))
    ax.text(11.05, 5.4, '89 mm\nbinnen', fontsize=8, va='center')
    fig.savefig(path, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def main(out):
    os.makedirs(out, exist_ok=True)
    pinout(os.path.join(out, 'pinout.png'))
    connection(os.path.join(out, 'aansluiten_rc522.png'), 'RC522-lezer aansluiten (8 draden)', 'RC522', [
        ('3.3V', 17, ''), ('GND', 20, ''), ('SDA', 24, 'CE0'), ('SCK', 23, ''), ('MOSI', 19, ''),
        ('MISO', 21, ''), ('IRQ', 18, ''), ('RST', 22, '')], C['rc522'],
        note='3.3V op pin 17, NOOIT op 5V. Geen kaart gelezen? Wissel MOSI en MISO om.')
    connection(os.path.join(out, 'aansluiten_versterker.png'), 'MAX98357A-versterker aansluiten (5 draden)',
               'MAX98357A', [('Vin', 2, '5V'), ('GND', 6, ''), ('BCLK', 12, ''), ('LRC', 35, ''), ('DIN', 40, ''),
                             ('GAIN', None, 'los laten (9 dB)'), ('SD', None, 'los laten (mono-mix)'),
                             ('+  -', None, 'speaker in de schroefklem')], C['amp'],
               note='De pinheader is al gesoldeerd: steek de Dupont-draadjes er direct op.')
    connection(os.path.join(out, 'aansluiten_knoppen.png'), 'Knoppen aansluiten (lip 1 via 1 kΩ naar de Pi)',
               'Knoppen', [('play/pauze', 33, 'midden'), ('vorige', 36, ''), ('volgende', 37, ''),
                           ('volume -', 15, 'links'), ('volume +', 16, 'rechts'),
                           ('alle lippen 2', 14, 'via GND-rail')], C['btn'])
    button_schema(os.path.join(out, 'knop_schema.png'))
    gnd_rail(os.path.join(out, 'gnd_rail.png'))
    led_schema(os.path.join(out, 'led_schema.png'))
    stack(os.path.join(out, 'stapeling.png'))
    print('schema\'s klaar in', out)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'schemas')
