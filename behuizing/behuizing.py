"""
Parametrische behuizing voor de muziekbox (Pi 3B + PiSugar 3 Plus, RC522, 5 knoppen van 16 mm, 79 mm speaker)

Speelse ovale vorm (superellips) met afgeronde randen, knoppen in een boog en een pilvormig NFC-vlak.
De speaker zit achter de gebogen voorwand op een vlakke speakerplaat.

Maakt STL-bestanden voor de Prusa:
  stl/onderbak.stl    - bak met speakerrooster en -plaat, kooi voor Pi/PiSugar, schroefpalen, ventilatie en USB-C-doorvoer
  stl/deksel.stl      - deksel met ruggen, NFC-vlak, 5 knopgaten met symbolen, aan-knop, LED-gat;
                        staat ondersteboven (bovenkant op het bed), tweekleurig met een filamentwissel op FACE_T
  stl/kooibeugel.stl  - beugel die de Pi in de kooi vastzet (2x M3)
  stl/drukstift.stl   - stiftje achter het paperclip-gaatje naar de aan/uit-knop van de PiSugar

Alle maten in mm. Pas de waarden in PARAMETERS aan na het opmeten van je onderdelen
en draai opnieuw:  python behuizing.py   (controleert ook of alles past)
Vereist: pip install manifold3d trimesh numpy
"""
import math
import os

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, set_circular_segments

set_circular_segments(96)

# ---------------------------------------------------------------------------
# PARAMETERS
# ---------------------------------------------------------------------------
W, D, H = 150.0, 136.0, 95.0    # buitenmaat (x = breedte, y = diepte met voorkant op y=0, z = hoogte)
SHAPE_N = 2.6                   # vorm: 2 = ellips, 2.5-3 = 'squircle', hoger = meer rechthoekig
WALL = 3.0                      # wanddikte (minimaal 3 mm)
FLOOR = 3.0                     # bodemdikte
LID = 3.0                       # dikte deksel
EDGE_R_BASE = 0.0               # afronding van de onderrand (0 = scherp; een ronding onderaan print slecht)
LID_CHAMFER = 1.5               # schuine bovenrand van het deksel; 45 graden print zonder support op het bed
FACE_T = 0.6                    # zichtlaag van het deksel: 3 lagen van 0,2 mm, daarna filamentwissel

# Speaker (frame 79 x 79, montagegaten 4 mm), op een vlakke plaat achter de gebogen voorwand
SPK_FRAME = 79.0
SPK_Z = 47.5                    # hoogte hart speaker
SPK_CONE_HOLE = 70.0            # opening in de speakerplaat
SPK_DEPTH = 46.0                # diepte van de speaker achter de plaat
SPK_GRILLE_R = 33.0             # straal van het gaatjesrooster in de voorwand
SPK_GRILLE_DIAMOND = 3.0        # ruitjes, van punt tot punt (vingers en potloden blijven buiten)
SPK_GRILLE_PITCH = 5.0
SPK_HOLE_SPACING_MIN = 57.0     # sleufgaten dekken een gatafstand van ... tot ... (vierkant) af
SPK_HOLE_SPACING_MAX = 61.0     # gemeten: 59
SPK_SCREW = 4.2
BAFFLE_T = 3.0                  # dikte speakerplaat
NUT_GAP = 6.0                   # ruimte voor de M4-moeren tussen voorwand en speakerplaat

# Knoppen (gemeten): huls rond 15,8 mm met 2 vlakke kanten op 14,8 mm, draad 9 mm, kraag 19 mm, moer 22 mm,
# 19 mm diep onder het deksel (tot de soldeerlippen). In een boog langs de achterrand.
BTN_HOLE = 16.2
BTN_FLATS = 15.1                # afstand tussen de vlakke kanten (tegen meedraaien)
BTN_DEPTH = 19.0                # onderkant kraag tot onderkant soldeerlippen
BTN_COLLAR = 19.0               # kraag bovenop het deksel
BTN_PITCH = 25.0                # afstand langs de boog; moeren van ~22 mm mogen elkaar niet raken
BTN_INSET = 21.0                # afstand van het hart van de knoppen tot de binnenkant van de wand
BTN_NUT = 22.0
BTN_SYMBOL = 7.0                # grootte van de gegraveerde symbolen
BTN_SYMBOLS = ['minus', 'prev', 'play', 'next', 'plus']   # van links naar rechts

# NFC-vlak (pilvorm, kaart 86 x 54) boven de RC522
NFC_W, NFC_D = 88.0, 56.0
NFC_Y = 12.0                    # voorrand van het vlak vanaf de voorkant
NFC_T = 2.0                     # dikte boven de RC522; 1,8 mm las met gemak, dus wat dikker kan
NFC_GROOVE = 1.2                # breedte van de pil-omtrek in de zichtlaag
RC522_W, RC522_D = 61.0, 40.5   # omtrek van de RC522; ligt in een kamer aan de onderkant van het deksel
RC522_GAP = 0.3                 # speling rondom in die kamer

LED_HOLE = 5.2

# Raspberry Pi 3B (85 x 56, gaten 58 x 49, 3,5 mm uit de SD-kaartrand) met de PiSugar eronder.
# Micro-USB-rand tegen de achterwand, USB-poorten links, SD-kaart rechts.
PI_W, PI_D = 85.0, 56.0
PI_MARGIN = 2.5                 # vrije ruimte rond de Pi
# De accu dekt de schroefgaten af. Het pakket staat daarom in een kooi: wanden rondom tot boven de PiSugar-print,
# en een beugel over de achterkant van de Pi die op twee paaltjes wordt geschroefd. Hoogtes boven de onderkant van de accu.
STACK_CLEAR = 0.6               # ribbels onder de accu
PISUGAR_PCB_H = 13.0            # onderkant print PiSugar (gemeten)
STACK_H = 34.0                  # bovenkant USB-/netwerkpoorten (gemeten)
PI_PCB_TOP = 16.0               # bovenkant print van de Pi (gemeten)
PI_SCREW_TOP = PI_PCB_TOP + 2.0 # bovenkant schroefkopjes op de Pi (kopjes 2 mm, gemeten)
ETH_TOP = 31.0                  # bovenkant netwerkpoort, waar de beugel overheen loopt (gemeten)
CAGE_T = 2.0                    # wanddikte kooi
CAGE_H = PI_PCB_TOP - 0.5       # hoogte kooiwanden: om beide printen heen, net onder de uitstekende USB-poorten
CAGE_ARM_BACK = 4.0             # achterkant open (USB-C, knop), alleen korte hoekstukjes
CAGE_GAP = 0.5                  # speling rond het pakket
CLAMP_W, CLAMP_T = 10.0, 3.0    # beugel: breedte en dikte
CLAMP_DY = 50.0                 # hart beugel vanaf de voorrand van de Pi
CLAMP_GAP = 0.3                 # lucht tussen beugel en poorten / schroefkopje
CLAMP_POST_D = 8.0
INSERT_M3 = 4.0                 # gat voor draadinzetstuk M3 (gemeten: 4,5 mm buiten, 5 mm lang)
INSERT_DEPTH = 6.0

# Achterwand: USB-C-doorvoer en aan/uit-gaatje (x t.o.v. de linkerrand van de Pi, z boven de onderkant van de accu)
# Gemeten vanaf de SD-kaartrand: USB-C 12,5 mm, knop 31 mm, beide ~12 mm hoog; knop steekt 1 mm buiten de Pi
STACK_Z = FLOOR + STACK_CLEAR
USBC_DX, USBC_Z = PI_W - 12.5, STACK_Z + 12.0
USBC_SLOT = (14.0, 8.5)        # ruim genoeg voor de stekkerkop van een gewone USB-C-kabel
USBC_SCREW_SPACING = 0.0        # 0 = geen schroefgaten (bij 28 mm botst het rechtergat met het paperclip-gaatje)
PUSH_DX, PUSH_Z = PI_W - 31.0, STACK_Z + 12.0   # hart van het paperclip-gaatje / de PiSugar-knop
PUSH_OUT = 1.0                  # knop steekt zoveel buiten de rand van de Pi
PUSH_GAP = 0.3                  # speling tussen stiftje en knop in rust
PIN_HOLE = 2.5
PUSH_HOLE = 6.4                 # binnenmaat geleidebuisje
SLEEVE_D = 10.0
SLEEVE_LEN = 3.0
PUSH_ROD_D = 5.8

# Ventilatie in de achterwand boven de Pi: ruitjes in een verspringend raster
VENT_DIAMOND = 3.0              # ruitje, van punt tot punt
VENT_PITCH = 6.0
VENT_COLS, VENT_ROWS = 8, 7
VENT_Z = 58.0                   # hart onderste rij

POST_D = 10.0                   # schroefpalen voor het deksel
POST_ANGLES = (28.0, 152.0, 208.0, 332.0)   # posities langs de wand, in graden (0 = rechts, 90 = achter)

# Ruggen onder het deksel. De onderbak ligt vast: boven de speakerplaat is 4 mm vrij, achter de speaker veel meer.
RIB_T = 2.4                     # dikte van de ruggen (6 lijnen van 0,4 mm)
RIB_LOW = 3.5                   # rand langs de wand (loopt ook over de speakerplaat); valt in de bak en lijnt het deksel uit
RIM_LEAD = 1.0                  # schuine inloop aan de buitenkant van die rand (wijst bij het printen omhoog)
RIB_TALL = 8.0                  # ruggen achter de speaker
RIB_WALL_GAP = 0.4              # speling tussen rand en binnenkant van de wand
RIB_CROSS_Y = 63.2              # dwarsrug tussen de speaker en de aan-knop
RIB_ARC_INSET = 39.5            # boogrug voor de knoppenrij, afstand vanaf de buitenkant
RIB_TIE_X = 20.0                # twee langsruggen naast de aan-knop, afstand vanaf het midden
RIB_NUT_CLEAR = 12.5            # vrije straal rond elke knop; de moer draai je aan vanaf de open achterkant
RIB_PAD = 1.5                   # extra dikte van de strook met de knoppenrij (tussen de boogrug en de rand)
BTN_THREAD = 9.0                # draadlengte van de knop
BTN_NUT_T = 4.0                 # minimaal nodig voor de moer

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stl')
CX, CY = W / 2, D / 2


# ---------------------------------------------------------------------------
# Vorm
# ---------------------------------------------------------------------------
def _se(t, a, b, n=SHAPE_N):
    c, s = math.cos(t), math.sin(t)
    return (CX + a * math.copysign(abs(c) ** (2 / n), c), CY + b * math.copysign(abs(s) ** (2 / n), s))


def outline(offset=0.0, steps=360):
    """Superellips-omtrek van de box, eventueel naar binnen (negatief) verschoven"""
    pts = [_se(2 * math.pi * i / steps, W / 2, D / 2) for i in range(steps)]
    cs = CrossSection([pts])
    return cs.offset(offset, JoinType.Round) if offset else cs


def half_depth(dx, inset=0.0):
    """Halve diepte van de (naar binnen verschoven) superellips op afstand dx van het midden"""
    a, b = W / 2 - inset, D / 2 - inset
    u = min(abs(dx) / a, 1.0)
    return b * (1 - u ** SHAPE_N) ** (1 / SHAPE_N)


def half_width(dy, inset=0.0):
    a, b = W / 2 - inset, D / 2 - inset
    u = min(abs(dy) / b, 1.0)
    return a * (1 - u ** SHAPE_N) ** (1 / SHAPE_N)


def front_inner(x):
    return CY - half_depth(x - CX, WALL)


def back_inner(x):
    return CY + half_depth(x - CX, WALL)


def back_outer(x):
    return CY + half_depth(x - CX)


def rounded_extrude(cs, h, r_bottom=0.0, r_top=0.0, steps=6):
    """Extrusie met afgeronde onder- en/of bovenrand (opgebouwd uit dunne plakjes)"""
    parts = [cs.extrude(h - r_bottom - r_top).translate([0, 0, r_bottom])]
    for r, bottom in ((r_bottom, True), (r_top, False)):
        if r <= 0:
            continue
        for i in range(steps):
            z0, z1 = r * i / steps, r * (i + 1) / steps
            zm = (z0 + z1) / 2
            inset = r - math.sqrt(max(r * r - (r - zm) ** 2, 0))
            sl = cs.offset(-inset, JoinType.Round).extrude(z1 - z0)
            parts.append(sl.translate([0, 0, z0 if bottom else h - z1]))
    return Manifold.batch_boolean(parts, manifold3d_add())


def chamfered_extrude(cs, h, c):
    """Extrusie van een convexe omtrek met een schuine bovenrand"""
    top = cs.offset(-c, JoinType.Round).extrude(0.01).translate([0, 0, h - 0.01])
    return (cs.extrude(h - c) + top).hull()


def manifold3d_add():
    from manifold3d import OpType
    return OpType.Add


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def rounded_rect(w, d, r):
    r = min(r, w / 2 - 0.01, d / 2 - 0.01)
    pts = []
    for cx, cy, a0 in [(w - r, r, -90), (w - r, d - r, 0), (r, d - r, 90), (r, r, 180)]:
        for i in range(17):
            a = math.radians(a0 + i * 90 / 16)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return CrossSection([pts])


def box(w, d, h, r=0.0):
    if r > 0:
        return rounded_rect(w, d, r).extrude(h)
    return Manifold.cube([w, d, h])


def ydiamond(d, y0, y1, x, z):
    """Ruitvormig gat van y0 tot y1 (punten boven/onder, zijkanten onder 45 graden: print zonder support)"""
    a = d / math.sqrt(2)
    return at(Manifold.cube([a, y1 - y0, a], True).rotate([0, 45, 0]), x, (y0 + y1) / 2, z)


def cyl(d, h, center=False):
    return Manifold.cylinder(h, d / 2, d / 2, 0, center)


def at(m, x=0.0, y=0.0, z=0.0):
    return m.translate([x, y, z])


def ycyl(d, y0, y1, x, z):
    """Cilinder langs de y-as van y0 tot y1"""
    return at(cyl(d, y1 - y0).rotate([-90, 0, 0]), x, y0, z)


def poly(points, h):
    # CrossSection verwacht polygonen tegen de klok in
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]))
    if area < 0:
        points = points[::-1]
    return CrossSection([points]).extrude(h)


def symbol(kind, size=9.0, h=1.0):
    """Gegraveerd symbool rond (0,0) in het xy-vlak"""
    s = size
    tri = lambda x0, flip=1: [(x0, -s / 2), (x0 + flip * s * 0.8, 0), (x0, s / 2)]  # noqa: E731
    if kind == 'minus':
        return at(box(s * 1.2, s * 0.3, h), -s * 0.6, -s * 0.15)
    if kind == 'plus':
        return at(box(s * 1.2, s * 0.3, h), -s * 0.6, -s * 0.15) + at(box(s * 0.3, s * 1.2, h), -s * 0.15, -s * 0.6)
    if kind == 'next':
        return poly(tri(-s * 0.8), h) + poly(tri(0.0), h)
    if kind == 'prev':
        return poly(tri(s * 0.8, -1), h) + poly(tri(0.0, -1), h)
    if kind == 'play':
        return (poly(tri(-s * 0.75), h)
                + at(box(s * 0.22, s, h), s * 0.25, -s / 2) + at(box(s * 0.22, s, h), s * 0.6, -s / 2))
    raise ValueError(kind)


def stadium(w, d):
    r = d / 2
    pts = [(w / 2 - r + r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in range(-90, 91, 6)]
    pts += [(-w / 2 + r + r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in range(90, 271, 6)]
    return CrossSection([pts])


# ---------------------------------------------------------------------------
# Indeling (afgeleid van de vorm)
# ---------------------------------------------------------------------------
def baffle_y():
    """Voorkant van de speakerplaat: ruimte voor de moeren bij de verste sleufgaten, en frame binnen de wand"""
    xs = SPK_HOLE_SPACING_MAX / 2
    need_nut = front_inner(CX + xs) + NUT_GAP
    need_frame = front_inner(CX + SPK_FRAME / 2) + 1.0 - BAFFLE_T
    return max(need_nut, need_frame, WALL + 4.0)


def pi_origin():
    """Pi zo ver mogelijk naar achteren, binnen de gebogen achterwand"""
    x0 = CX - PI_W / 2
    y_top = min(back_inner(x0 - 2), back_inner(x0 + PI_W)) - PI_MARGIN   # incl. 2 mm uitstekende USB-poorten
    return (x0, y_top - PI_D)


def cage_boxes():
    """Kooiwanden rond de voetafdruk van Pi/PiSugar, als (x, y, w, d)"""
    x0, y0 = pi_origin()
    g, t = CAGE_GAP, CAGE_T
    xl, xr = x0 - g - t, x0 + PI_W + g
    yf, yb = y0 - g - t, y0 + PI_D + g
    return [(xl, yf, xr + t - xl, t),                        # voor
            (xl, yf, t, yb + t - yf), (xr, yf, t, yb + t - yf),   # zijkanten
            (xl, yb, CAGE_ARM_BACK + t, t), (xr - CAGE_ARM_BACK, yb, CAGE_ARM_BACK + t, t)]


def clamp_posts():
    """Paaltjes voor de beugel, links (buiten de uitstekende USB-poorten) en rechts van de kooi"""
    x0, y0 = pi_origin()
    y = y0 + CLAMP_DY
    return [(x0 - 2.5 - CAGE_GAP - CLAMP_POST_D / 2, y), (x0 + PI_W + CAGE_GAP + CAGE_T + CLAMP_POST_D / 2 - 1.0, y)]


def clamp_z():
    return STACK_Z + STACK_H + CLAMP_GAP


def lid_post_positions():
    pts = []
    inset = WALL + POST_D / 2 - 1.0
    for ang in POST_ANGLES:
        t = math.radians(ang)
        x, y = _se(t, W / 2 - inset, D / 2 - inset)
        pts.append((x, y))
    return pts


def button_positions():
    """Knoppen op een boog evenwijdig aan de achterwand, op gelijke afstand langs de boog"""
    inset = WALL + BTN_INSET
    xs = np.linspace(CX - W / 2 + inset + 1, CX + W / 2 - inset - 1, 4001)
    ys = np.array([CY + half_depth(x - CX, inset) for x in xs])
    s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(xs), np.diff(ys)))])
    mid = np.interp(CX, xs, s)
    n = len(BTN_SYMBOLS)
    out = []
    for i in range(n):
        si = mid + (i - (n - 1) / 2) * BTN_PITCH
        out.append((float(np.interp(si, s, xs)), float(np.interp(si, s, ys))))
    return out


def button_hole(angle):
    """Rond gat met twee vlakke kanten; de vlakke kanten staan dwars op de richting naar het symbool"""
    h = LID + RIB_PAD + 2
    flats = at(box(BTN_FLATS, BTN_HOLE + 2, h), -BTN_FLATS / 2, -(BTN_HOLE + 2) / 2)
    return (cyl(BTN_HOLE, h) ^ flats).rotate([0, 0, angle])


def symbol_positions():
    """Symbool vóór elke knop (richting het midden van de box)"""
    out = []
    for x, y in button_positions():
        dx, dy = CX - x, (CY - 5) - y
        L = math.hypot(dx, dy)
        dist = BTN_HOLE / 2 + 6.5
        out.append((x + dx / L * dist, y + dy / L * dist))
    return out


def power_button_position():
    """Aan-knop (parallel aan de knop van de PiSugar): midden tussen het NFC-vlak en het play-symbool"""
    nfc_back = nfc_center()[1] + NFC_D / 2
    play_sym = symbol_positions()[BTN_SYMBOLS.index('play')][1] - BTN_SYMBOL / 2
    return (CX, (nfc_back + play_sym) / 2)


def led_position():
    b = button_positions()
    (x1, y1), (x2, y2) = b[2], b[3]
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    return (mx, my + 13.0)


def rib_sections():
    """Doorsneden onder het deksel: (lage rand, hoge ruggen, verdikte strook bij de knoppen)"""
    rect = lambda x, y, w, d: CrossSection.square([w, d]).translate([x, y])  # noqa: E731
    inner = outline(-(WALL + RIB_WALL_GAP))
    rim = inner - outline(-(WALL + RIB_WALL_GAP + RIB_T))
    arc = outline(-RIB_ARC_INSET) - outline(-(RIB_ARC_INSET + RIB_T))
    tall = rect(0, RIB_CROSS_Y - RIB_T / 2, W, RIB_T) + (arc ^ rect(0, RIB_CROSS_Y, W, D))
    tie_top = CY + half_depth(RIB_TIE_X, RIB_ARC_INSET + RIB_T / 2)
    for x in (CX - RIB_TIE_X, CX + RIB_TIE_X):
        tall += rect(x - RIB_T / 2, RIB_CROSS_Y, RIB_T, tie_top - RIB_CROSS_Y)
    tall ^= outline(-(WALL + RIB_WALL_GAP + RIB_T / 2))   # eindigt midden in de rand
    posts = [CrossSection.circle(POST_D / 2 + 0.5).translate(p) for p in lid_post_positions()]
    nuts = [CrossSection.circle(RIB_NUT_CLEAR).translate(p) for p in button_positions() + [power_button_position()]]
    for keep_out in posts + nuts:
        tall -= keep_out
    pad = (outline(-(WALL + RIB_WALL_GAP + RIB_T * 0.75)) - outline(-(RIB_ARC_INSET + RIB_T / 2))) ^ rect(0, RIB_CROSS_Y, W, D)
    for keep_out, p in zip(posts, lid_post_positions()):
        rim -= keep_out
        pad -= CrossSection.circle(POST_D / 2 + 1.0).translate(p)
    return rim, tall, pad


def usbc_pos():
    return (pi_origin()[0] + USBC_DX, USBC_Z)


def push_pos():
    return (pi_origin()[0] + PUSH_DX, PUSH_Z)


def nfc_center():
    return (CX, NFC_Y + NFC_D / 2)


# ---------------------------------------------------------------------------
# Controle: past alles?
# ---------------------------------------------------------------------------
def check_layout():
    problems = []
    by = baffle_y()
    spk_back = by + BAFFLE_T + SPK_DEPTH
    x0, y0 = pi_origin()
    cage_front = y0 - CAGE_GAP - CAGE_T
    if cage_front < spk_back + 1:
        problems.append(f"Kooi botst met de speaker: kooi begint op y={cage_front:.1f}, speaker eindigt op y={spk_back:.1f}")
    for x, y in [(x0 - 2, y0), (x0 + PI_W, y0)]:
        if abs(y - CY) > half_depth(x - CX, WALL) - PI_MARGIN + 0.01:
            problems.append(f"Pi-hoek ({x:.1f},{y:.1f}) valt buiten de wand")
    for x, y in lid_post_positions():
        r = POST_D / 2
        # niet in de Pi (volle hoogte)
        if x0 - 2 - r < x < x0 + PI_W + r and y0 - r < y < y0 + PI_D + r:
            problems.append(f"Schroefpaal ({x:.1f},{y:.1f}) botst met de Pi")
        # niet in het speakerframe / de speaker
        if abs(x - CX) < SPK_FRAME / 2 + r and by - r < y < spk_back + r:
            problems.append(f"Schroefpaal ({x:.1f},{y:.1f}) botst met de speaker")
        for bx, bym in button_positions():
            if math.hypot(x - bx, y - bym) < BTN_NUT / 2 + r:
                problems.append(f"Schroefpaal ({x:.1f},{y:.1f}) botst met knop ({bx:.1f},{bym:.1f})")
        rx0, ry0 = CX - RC522_W / 2, nfc_center()[1] - RC522_D / 2
        if rx0 - r < x < rx0 + RC522_W + r and ry0 - r < y < ry0 + RC522_D + r:
            problems.append(f"Schroefpaal ({x:.1f},{y:.1f}) botst met de RC522")
    bp = button_positions()
    for (ax, ay), (bx, bym) in zip(bp, bp[1:]):
        if math.hypot(ax - bx, ay - bym) < BTN_NUT + 1:
            problems.append("Knoppen staan te dicht op elkaar")
    for x, y in bp:
        if half_depth(x - CX, WALL) - abs(y - CY) < BTN_NUT / 2 - 3 and half_width(y - CY, WALL) - abs(x - CX) < 9:
            problems.append(f"Knop ({x:.1f},{y:.1f}) zit te dicht bij de wand")
    nx, ny = nfc_center()
    for (sx, sy) in symbol_positions():
        # symbool mag niet in het NFC-vlak vallen
        dxn = max(abs(sx - nx) - (NFC_W / 2 - NFC_D / 2), 0)
        if math.hypot(dxn, sy - ny) < NFC_D / 2 + BTN_SYMBOL * 0.7:
            problems.append(f"Symbool ({sx:.1f},{sy:.1f}) valt in het NFC-vlak")
    for y in (NFC_Y, NFC_Y + NFC_D):
        if abs(y - CY) > half_depth(NFC_W / 2 - NFC_D / 2, WALL) - 2:
            problems.append("NFC-vlak valt buiten de box")
    px, py = power_button_position()
    for bx, bym in bp:
        if math.hypot(px - bx, py - bym) < BTN_NUT + 1:
            problems.append("Aan-knop staat te dicht op een andere knop")
    if py - BTN_COLLAR / 2 - (ny + NFC_D / 2) < 1.5:
        problems.append("Aan-knop zit te dicht op het NFC-vlak")
    for sx, sy in symbol_positions():
        if math.hypot(px - sx, py - sy) < BTN_COLLAR / 2 + BTN_SYMBOL / 2 + 1.5:
            problems.append(f"Aan-knop valt over het symbool op ({sx:.1f},{sy:.1f})")
    if py - BTN_NUT / 2 < ny + RC522_D / 2 + 1:
        problems.append("Moer van de aan-knop botst met de RC522")
    baffle_top = SPK_Z + SPK_FRAME / 2 + 1.0
    if H - LID - RIB_LOW < baffle_top + 0.5:
        problems.append("Rand onder het deksel raakt de speakerplaat")
    rib_front = RIB_CROSS_Y - RIB_T / 2
    if rib_front < by + BAFFLE_T + SPK_DEPTH + 0.5:
        problems.append("Dwarsrug botst met de speaker")
    if rib_front < ny + RC522_D / 2 + RC522_GAP + 1:
        problems.append("Dwarsrug botst met de RC522")
    if BTN_THREAD - LID - RIB_PAD < BTN_NUT_T:
        problems.append("Te weinig schroefdraad over voor de moer")
    btn_bottom = H - LID - BTN_DEPTH
    if btn_bottom < clamp_z() + CLAMP_T + 3:
        problems.append(f"Knoppen komen tot z={btn_bottom:.1f}, te dicht op de kooibeugel")
    for bx, bym in bp + [(px, py)]:
        if bym - BTN_NUT / 2 < baffle_y() + BAFFLE_T + SPK_DEPTH and btn_bottom < SPK_Z + SPK_FRAME / 2:
            problems.append(f"Knop ({bx:.1f},{bym:.1f}) botst met de speaker")
    lx, ly = led_position()
    if half_depth(lx - CX, WALL) - abs(ly - CY) < 5:
        problems.append("LED zit te dicht bij de wand")
    for bx, bym in bp:
        if math.hypot(lx - bx, ly - bym) < 10 + LED_HOLE / 2:
            problems.append("LED zit onder een knop")
    return problems


# ---------------------------------------------------------------------------
# Onderbak
# ---------------------------------------------------------------------------
def make_base():
    h = H - LID
    outer = rounded_extrude(outline(), h, r_bottom=EDGE_R_BASE)
    inner = outline(-WALL).extrude(h).translate([0, 0, FLOOR])
    base = outer - inner
    inner_region = outline(-WALL + 0.01).extrude(h)   # om binnenonderdelen tegen de wand af te kappen

    # Schroefpalen deksel
    for x, y in lid_post_positions():
        base += at(cyl(POST_D, h), x, y)
        base -= at(cyl(INSERT_M3, INSERT_DEPTH + 0.01), x, y, h - INSERT_DEPTH)

    # Kooi Pi/PiSugar met ribbels onder de accu en paaltjes voor de beugel
    for x, y, w, d in cage_boxes():
        base += at(box(w, d, STACK_Z + CAGE_H - 1), x, y, 1) ^ inner_region
    x0, y0 = pi_origin()
    for f in (0.15, 0.5, 0.85):
        base += at(box(3.0, PI_D - 6, STACK_Z - 1), x0 + f * PI_W - 1.5, y0 + 3, 1)
    # uitsparing voor de microSD-kaart (steekt ~2,5 mm uit, midden op de SD-kant, onder de Pi-print)
    zs = STACK_Z + PI_PCB_TOP - 1.4 - 2.0
    base -= at(box(CAGE_GAP + CAGE_T + 2, 16.0, STACK_Z + CAGE_H - zs + 1), x0 + PI_W - 1, y0 + PI_D / 2 - 8.0, zs)
    for x, y in clamp_posts():
        base += at(cyl(CLAMP_POST_D, clamp_z() - 1), x, y, 1) ^ inner_region
        base -= at(cyl(INSERT_M3, INSERT_DEPTH + 0.01), x, y, clamp_z() - INSERT_DEPTH)

    # Speakerplaat: vlak, van wand tot wand, tot net boven het speakerframe
    by = baffle_y()
    top = SPK_Z + SPK_FRAME / 2 + 1.0
    plate = at(box(W, BAFFLE_T, top), 0, by, 0) ^ inner_region
    cx, cz = CX, SPK_Z
    plate -= ycyl(SPK_CONE_HOLE, by - 1, by + BAFFLE_T + 1, cx, cz)
    rmin = SPK_HOLE_SPACING_MIN / math.sqrt(2)
    rmax = SPK_HOLE_SPACING_MAX / math.sqrt(2)
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        for k in range(9):
            r = rmin + (rmax - rmin) * k / 8
            plate -= ycyl(SPK_SCREW, by - 1, by + BAFFLE_T + 1, cx + r * math.cos(a), cz + r * math.sin(a))
    base += plate

    # Gaatjesrooster in de gebogen voorwand (alleen tot de speakerplaat)
    pitch = SPK_GRILLE_PITCH
    grille = []
    row = 0
    zz = -SPK_GRILLE_R
    while zz <= SPK_GRILLE_R:
        off = (pitch / 2) if row % 2 else 0.0
        xx = -SPK_GRILLE_R + off
        while xx <= SPK_GRILLE_R:
            if math.hypot(xx, zz) <= SPK_GRILLE_R - SPK_GRILLE_DIAMOND / 2:
                grille.append(ydiamond(SPK_GRILLE_DIAMOND, -1, by - 0.5, cx + xx, cz + zz))
            xx += pitch
        zz += pitch / 2
        row += 1
    base -= Manifold.batch_boolean(grille, manifold3d_add())

    # Achterwand: USB-C-doorvoer
    ux, uz = usbc_pos()
    yi = back_inner(ux) - 2
    base -= at(box(USBC_SLOT[0], D + 2 - yi, USBC_SLOT[1]), ux - USBC_SLOT[0] / 2, yi, uz - USBC_SLOT[1] / 2)
    if USBC_SCREW_SPACING:
        for sx in (-USBC_SCREW_SPACING / 2, USBC_SCREW_SPACING / 2):
            base -= ycyl(3.2, back_inner(ux + sx) - 2, D + 1, ux + sx, uz)

    # Achterwand: aan/uit (paperclip-gaatje, binnen een geleidebuisje)
    px, pz = push_pos()
    yi = back_inner(px)
    base += ycyl(SLEEVE_D, yi - SLEEVE_LEN, yi + 1.5, px, pz) - ycyl(PUSH_HOLE, yi - SLEEVE_LEN - 1, yi, px, pz)
    base -= ycyl(PIN_HOLE, yi - 1, D + 1, px, pz)

    # Achterwand: ventilatie als ruitjes (te klein om er iets in te stoppen, printen zonder support)
    vents = []
    for row in range(VENT_ROWS):
        off = VENT_PITCH / 2 if row % 2 else 0.0
        cols = VENT_COLS - (1 if row % 2 else 0)
        z = VENT_Z + row * VENT_PITCH / 2
        for i in range(cols):
            x = CX - (VENT_COLS - 1) * VENT_PITCH / 2 + off + i * VENT_PITCH
            y0 = back_inner(x) - 3
            vents.append(ydiamond(VENT_DIAMOND, y0, D + 2, x, z))
    base -= Manifold.batch_boolean(vents, manifold3d_add())

    return base


# ---------------------------------------------------------------------------
# Deksel
# ---------------------------------------------------------------------------
def make_lid():
    lid = chamfered_extrude(outline(), LID, LID_CHAMFER)

    # Ruggen aan de onderkant
    rim, tall, pad = rib_sections()
    lid += at(rim.extrude(RIB_LOW + 0.5), 0, 0, -RIB_LOW)
    lid += at(pad.extrude(RIB_PAD + 0.5), 0, 0, -RIB_PAD)
    lid += at(tall.extrude(RIB_TALL + 0.5), 0, 0, -RIB_TALL)
    # Schuine inloop aan de buitenkant van de rand
    steps = 4
    for i in range(steps):
        f = (steps - i) / steps
        cut = outline() - outline(-(WALL + RIB_WALL_GAP + RIM_LEAD * f))
        lid -= at(cut.extrude(RIM_LEAD * (1 - f + 1 / steps) + 1), 0, 0, -RIB_LOW - 1)

    # NFC-vlak: pilvormige omtrek in de zichtlaag; de kaart ligt op een vlakke bovenkant
    nx, ny = nfc_center()
    groove = stadium(NFC_W, NFC_D) - stadium(NFC_W - 2 * NFC_GROOVE, NFC_D - 2 * NFC_GROOVE)
    lid -= at(groove.extrude(FACE_T + 0.01), nx, ny, LID - FACE_T)
    # Kamer aan de onderkant: hierin ligt de RC522 (antenne tegen het deksel)
    lid -= at(box(RC522_W + 2 * RC522_GAP, RC522_D + 2 * RC522_GAP, LID - NFC_T + 0.01),
              nx - RC522_W / 2 - RC522_GAP, ny - RC522_D / 2 - RC522_GAP, -0.01)

    # Knopgaten met gegraveerd symbool ervoor
    for (x, y), (sx, sy), kind in zip(button_positions(), symbol_positions(), BTN_SYMBOLS):
        lid -= at(button_hole(math.degrees(math.atan2(sy - y, sx - x))), x, y, -RIB_PAD - 1)
        lid -= at(symbol(kind, BTN_SYMBOL, FACE_T + 0.01), sx, sy, LID - FACE_T)

    # Aan-knop, vlakke kanten net als bij de play-knop
    px, py = power_button_position()
    lid -= at(button_hole(-90), px, py, -RIB_PAD - 1)

    # LED
    lx, ly = led_position()
    lid -= at(cyl(LED_HOLE, LID + RIB_PAD + 2), lx, ly, -RIB_PAD - 1)

    # Verzonken schroefgaten M3
    for x, y in lid_post_positions():
        lid -= at(cyl(3.4, LID + 2), x, y, -1)
        lid -= at(Manifold.cylinder(1.8, 1.7, 3.4, 0, False), x, y, LID - 1.79)

    return lid


def make_clamp():
    """Beugel over de achterkant van de Pi: blokje op de netwerkpoort, nokje op het schroefkopje bij de SD-kaart"""
    (xa, y), (xb, _) = clamp_posts()
    x0, y0 = pi_origin()
    r = CLAMP_POST_D / 2
    bar = at(box(xb - xa + 2 * r, CLAMP_W, CLAMP_T, r=CLAMP_W / 2 - 0.01), xa - r, y - CLAMP_W / 2)
    nx, ny = x0 + PI_W - 3.5, y0 + 52.5
    nub_h = clamp_z() - (STACK_Z + PI_SCREW_TOP + CLAMP_GAP)
    bar += at(cyl(6.0, nub_h + 0.01), nx, ny, -nub_h)
    eth_h = clamp_z() - (STACK_Z + ETH_TOP + CLAMP_GAP)
    bar += at(box(16.0, CLAMP_W, eth_h + 0.01), x0 + 1.0, y - CLAMP_W / 2, -eth_h)
    for px, py in clamp_posts():
        bar -= at(cyl(3.4, CLAMP_T + nub_h + 2), px, py, -nub_h - 1)
    return bar


def push_rod_len():
    """Binnenkant achterwand tot de PiSugar-knop, min wat speling (incl. kopje)"""
    px = push_pos()[0]
    return back_inner(px) - (pi_origin()[1] + PI_D + PUSH_OUT) - PUSH_GAP


def make_push_rod():
    return cyl(PUSH_ROD_D, push_rod_len()) + cyl(PUSH_HOLE + 3.0, 1.6)


# ---------------------------------------------------------------------------
def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts))


def build():
    return {'onderbak': make_base(),
            'deksel': at(make_lid().rotate([180, 0, 0]), 0, D, LID),   # ondersteboven: de ruggen wijzen omhoog
            'drukstift': make_push_rod(),
            'kooibeugel': make_clamp().rotate([180, 0, 0])}   # vlakke kant op het bed


def main():
    problems = check_layout()
    if problems:
        print("LET OP, het past niet:")
        for p in problems:
            print("  -", p)
    else:
        print("Indeling gecontroleerd: alles past.")
    os.makedirs(OUT, exist_ok=True)
    for name, m in build().items():
        t = to_trimesh(m)
        path = os.path.join(OUT, f'{name}.stl')
        t.export(path)
        ext = t.bounds[1] - t.bounds[0]
        print(f"{name:10s} {ext[0]:6.1f} x {ext[1]:6.1f} x {ext[2]:6.1f} mm  watertight={t.is_watertight}  -> {path}")


if __name__ == '__main__':
    main()
