"""
Renders van de behuizing en de assemblagestappen voor de handleiding (PNG).
Gebruik: python render.py <uitvoermap>
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

import behuizing as b  # noqa: E402
from zrender import ZScene  # noqa: E402

LIGHT = np.array([0.4, -0.7, 0.8])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def mesh_of(m, max_edge=5.0):
    # Kleine driehoeken: matplotlib sorteert per driehoek op diepte, lange smalle driehoeken geven artefacten
    t = b.to_trimesh(m)
    v, f = trimesh.remesh.subdivide_to_size(t.vertices, t.faces, max_edge=max_edge, max_iter=20)
    return v, f


def shade(color, normals, alpha=1.0):
    c = np.array(matplotlib.colors.to_rgb(color))
    k = 0.45 + 0.55 * np.clip(normals @ LIGHT, 0, 1)
    rgb = np.clip(c[None, :] * k[:, None], 0, 1)
    return np.column_stack([rgb, np.full(len(rgb), alpha)])


class Scene:
    """Verzamelt onderdelen en rendert ze met de z-buffer-renderer"""

    def __init__(self):
        self.z = ZScene()

    def add(self, m, color, offset=(0, 0, 0), alpha=1.0):
        t = b.to_trimesh(m)
        self.z.add(t.vertices + np.array(offset), t.faces, matplotlib.colors.to_rgb(color), alpha)
        return self

    def render(self, path, elev=24, azim=-58, title=None, labels=(), zoom=1.0, size=None):
        self.z.render(path, elev=elev, azim=azim, title=title, labels=labels)


class MplScene:
    def __init__(self):
        self.parts = []

    def add(self, m, color, offset=(0, 0, 0), alpha=1.0):
        v, f = mesh_of(m)
        self.parts.append((v + np.array(offset), f, color, alpha))
        return self

    def render(self, path, elev=24, azim=-58, title=None, labels=(), zoom=1.0, size=(8, 6)):
        fig = plt.figure(figsize=size, dpi=150)
        ax = fig.add_subplot(111, projection='3d')
        allv = []
        for v, f, color, alpha in self.parts:
            tris = v[f]
            n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
            n = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
            pc = Poly3DCollection(tris, facecolors=shade(color, n, alpha), edgecolors='none', linewidths=0)
            ax.add_collection3d(pc)
            allv.append(v)
        allv = np.vstack(allv)
        lo, hi = allv.min(0), allv.max(0)
        c = (lo + hi) / 2
        r = (hi - lo).max() / 2 / zoom
        ax.set_xlim(c[0] - r, c[0] + r)
        ax.set_ylim(c[1] - r, c[1] + r)
        ax.set_zlim(c[2] - r, c[2] + r)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        for (x, y, z, text) in labels:
            ax.text(x, y, z, text, fontsize=9, color='#111', ha='center',
                    bbox=dict(boxstyle='round,pad=0.25', fc='#fff8c4', ec='#999', lw=0.6))
        if title:
            ax.set_title(title, fontsize=12, pad=0)
        plt.subplots_adjust(0, 0, 1, 1)
        fig.savefig(path, bbox_inches='tight', pad_inches=0.05, facecolor='white')
        plt.close(fig)


# ---------------------------------------------------------------------------
# Vereenvoudigde onderdelen
# ---------------------------------------------------------------------------
Z_SUGAR = b.STACK_Z
SUGAR_H = b.PI_PCB_TOP - 1.6        # accu en PiSugar tot onderkant Pi
Z_PI = Z_SUGAR + SUGAR_H


def pisugar():
    x, y = b.pi_origin()
    return b.at(b.box(65.0, 56.0, SUGAR_H, 3), x + 10, y, Z_SUGAR)


def pi_board():
    x, y = b.pi_origin()
    pcb = b.at(b.box(b.PI_W, b.PI_D, 1.6, 3), x, y, Z_PI)
    usb = b.at(b.box(17, 13, 15), x - 2, y + 4, Z_PI + 1.6) + b.at(b.box(17, 15, 15), x - 2, y + 22, Z_PI + 1.6) \
        + b.at(b.box(21, 16, 13), x - 2, y + 39, Z_PI + 1.6)
    return pcb, usb


def pi_header():
    x, y = b.pi_origin()
    return b.at(b.box(51, 5, 8.5), x + b.PI_W - 58, y + 1, Z_PI + 1.6)   # GPIO aan de voorkant, richting speaker


def speaker():
    cx, cz = b.W / 2, b.SPK_Z
    yb = b.baffle_y() + b.BAFFLE_T
    frame = b.at(b.box(b.SPK_FRAME, 5, b.SPK_FRAME, 4), cx - b.SPK_FRAME / 2, yb, cz - b.SPK_FRAME / 2)
    cone = b.at(b.Manifold.cylinder(41, 36, 18, 0, False).rotate([-90, 0, 0]), cx, yb + 5, cz)
    return frame, cone


def rc522(z):
    rx, ry = b.nfc_center()[0] - b.RC522_W / 2, b.nfc_center()[1] - b.RC522_D / 2
    return b.at(b.box(b.RC522_W, b.RC522_D, 1.6), rx, ry, z)


def buttons(z_lid):
    caps, bodies = [], []
    for (x, y) in b.button_positions() + [b.power_button_position()]:
        caps.append(b.at(b.cyl(19, 3), x, y, z_lid + b.LID) + b.at(b.cyl(14, 6), x, y, z_lid + b.LID))
        bodies.append(b.at(b.cyl(16, b.BTN_DEPTH), x, y, z_lid - b.BTN_DEPTH))
    return caps, bodies


def amp():
    # MAX98357A met dubbelzijdig tape op de bodem, links naast de Pi
    x, y = b.pi_origin()
    return b.at(b.box(19, 18, 1.6), x - 23, y + 12, b.FLOOR)


BTN_COLORS = ['#d62828', '#1d4ed8', '#2a9d4b', '#1d4ed8', '#d62828', '#f4f4f4']   # laatste = aan-knop
C_BOX, C_LID, C_FACE = '#2f6fb5', '#2f6fb5', '#f4f4f4'


def add_lid(scene, lid, offset=(0, 0, 0), alpha=1.0):
    """Deksel in twee kleuren: zichtlaag en de rest (symbolen tonen de kleur eronder)"""
    face = lid ^ b.at(b.box(b.W, b.D, b.FACE_T + 1), 0, 0, b.LID - b.FACE_T)
    return scene.add(lid - face, C_LID, offset, alpha).add(face, C_FACE, offset, alpha)


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    base, lid, rod = b.make_base(), b.make_lid(), b.make_push_rod()
    zl = b.H - b.LID

    # 1. Behuizing los (voor- en achterkant) en deksel
    Scene().add(base, C_BOX).render(os.path.join(outdir, 'kast_voor.png'), azim=-62, title='Onderbak - voorkant')
    Scene().add(base, C_BOX).render(os.path.join(outdir, 'kast_achter.png'), azim=118, elev=20,
                                    title='Onderbak - achterkant',
                                    labels=[(b.usbc_pos()[0], b.D + 8, b.usbc_pos()[1] - 12, 'USB-C'),
                                            (b.push_pos()[0], b.D + 8, b.push_pos()[1] - 12, 'aan/uit (paperclip)'),
                                            (45, b.D + 8, 100, 'ventilatie')])
    add_lid(Scene(), lid).render(os.path.join(outdir, 'deksel.png'), elev=62, azim=-90, zoom=1.25,
                                 title='Deksel - bovenkant')
    add_lid(Scene(), lid).render(os.path.join(outdir, 'deksel_onder.png'), elev=-62, azim=-90, zoom=1.25,
                                 title='Deksel - onderkant met ruggen')

    # 2. Assemblagestappen
    pcb, usb = pi_board()
    frame, cone = speaker()
    caps, bodies = buttons(zl)

    s = Scene().add(base, C_BOX, alpha=0.35)
    s.render(os.path.join(outdir, 'stap1_inserts.png'), elev=48, azim=-60, title='Stap 1 - draadinzetstukken',
             labels=[(x, y, b.H + 4, 'M3') for x, y in b.lid_post_positions()[:2]])

    s = Scene().add(base, C_BOX, alpha=0.3).add(pisugar(), '#222222').add(pcb, '#2a9d4b').add(usb, '#b0b0b0') \
        .add(pi_header(), '#111111').add(b.at(b.make_clamp(), 0, 0, b.clamp_z()), '#f4a261')
    s.render(os.path.join(outdir, 'stap2_pi.png'), elev=40, azim=-55, title='Stap 2 - PiSugar en Pi in de kooi',
             labels=[(b.pi_origin()[0] + 40, b.pi_origin()[1] + 28, Z_PI + 30, 'Pi 3B'),
                     (b.pi_origin()[0] + 40, b.pi_origin()[1] - 6, Z_SUGAR + 4, 'PiSugar')])

    s = Scene().add(base, C_BOX, alpha=0.3).add(pisugar(), '#222222').add(pcb, '#2a9d4b').add(usb, '#b0b0b0') \
        .add(frame, '#333333').add(cone, '#555555').add(amp(), '#c1121f')
    s.render(os.path.join(outdir, 'stap3_speaker.png'), elev=30, azim=-35, title='Stap 3 - speaker en versterker',
             labels=[(b.W / 2, 30, b.SPK_Z + 50, 'speaker (M4)'),
                     (b.pi_origin()[0] - 14, b.pi_origin()[1] + 21, 30, 'MAX98357')])

    lid_up = (0, 0, zl)
    s = add_lid(Scene(), lid, lid_up, alpha=0.55)
    for m, col in zip(caps, BTN_COLORS):
        s.add(m, col)
    for m in bodies:
        s.add(m, '#444444')
    s.add(rc522(zl + b.LID - b.NFC_T - 1.6), '#1565c0')
    s.render(os.path.join(outdir, 'stap4_deksel.png'), elev=-28, azim=-60, zoom=1.15,
             title='Stap 4 - knoppen en RC522 in het deksel (onderaanzicht)')

    # Exploded view: alles samen
    up = 70
    s = Scene().add(base, C_BOX).add(pisugar(), '#222222').add(pcb, '#2a9d4b').add(usb, '#b0b0b0') \
        .add(frame, '#333333').add(cone, '#555555')
    add_lid(s, lid, (0, 0, zl + up))
    for m, col in zip(caps, BTN_COLORS):
        s.add(m, col, (0, 0, up))
    for m in bodies:
        s.add(m, '#444444', (0, 0, up))
    s.add(rc522(zl + b.LID - b.NFC_T - 1.6), '#1565c0', (0, 0, up))
    s.render(os.path.join(outdir, 'stap5_sluiten.png'), elev=22, azim=-55, title='Stap 5 - deksel erop (4x M3)')

    # Eindresultaat
    s = add_lid(Scene().add(base, C_BOX), lid, (0, 0, zl))
    for m, col in zip(caps, BTN_COLORS):
        s.add(m, col)
    s.render(os.path.join(outdir, 'eindresultaat.png'), elev=26, azim=-50, title='Eindresultaat')
    print('renders klaar in', outdir)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'renders')
