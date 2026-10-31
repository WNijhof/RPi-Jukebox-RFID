"""Kleine software-renderer (z-buffer, vlakke belichting, randlijnen) voor technische tekeningen."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

LIGHT = np.array([0.35, -0.55, 0.75])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def _font(size):
    for name in ('arial.ttf', 'segoeui.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def view_matrix(elev, azim):
    a, e = math.radians(azim), math.radians(elev)
    # camera kijkt naar de oorsprong vanuit (azim, elev); x' = rechts, y' = omhoog, z' = naar de camera
    fwd = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    up = np.array([0, 0, 1.0])
    right = np.cross(up, fwd)
    right /= np.linalg.norm(right)
    upv = np.cross(fwd, right)
    return np.vstack([right, upv, fwd])


def _raster(buf_z, buf_c, buf_n, buf_id, pts, col, nrm, pid):
    h, w = buf_z.shape
    x0, y0 = np.floor(pts[:, :2].min(0)).astype(int)
    x1, y1 = np.ceil(pts[:, :2].max(0)).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, w - 1), min(y1, h - 1)
    if x1 < x0 or y1 < y0:
        return
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = pts
    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-9:
        return
    xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
    l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
    l3 = 1 - l1 - l2
    inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
    if not inside.any():
        return
    z = l1 * az + l2 * bz + l3 * cz
    sub = buf_z[y0:y1 + 1, x0:x1 + 1]
    upd = inside & (z > sub)
    sub[upd] = z[upd]
    buf_c[y0:y1 + 1, x0:x1 + 1][upd] = col
    buf_n[y0:y1 + 1, x0:x1 + 1][upd] = nrm
    buf_id[y0:y1 + 1, x0:x1 + 1][upd] = pid


class ZScene:
    def __init__(self):
        self.parts = []   # (vertices, faces, rgb, alpha)

    def add(self, vertices, faces, rgb, alpha=1.0):
        self.parts.append((np.asarray(vertices, float), np.asarray(faces), np.asarray(rgb, float), alpha))

    def _layer(self, parts, R, scale, off, size):
        w, h = size
        zb = np.full((h, w), -np.inf)
        cb = np.ones((h, w, 3))
        nb = np.zeros((h, w, 3))
        ib = np.full((h, w), -1, int)
        for pid, (v, f, rgb, _a) in parts:
            pv = v @ R.T
            sx = (pv[:, 0] - off[0]) * scale
            sy = h - (pv[:, 1] - off[1]) * scale
            P = np.column_stack([sx, sy, pv[:, 2]])
            tris = v[f]
            n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
            n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
            k = 0.5 + 0.5 * np.abs(n @ LIGHT)
            for i, tri in enumerate(f):
                _raster(zb, cb, nb, ib, P[tri], np.clip(rgb * k[i], 0, 1), n[i], pid)
        return zb, cb, nb, ib

    @staticmethod
    def _edges(zb, nb, ib):
        e = np.zeros(zb.shape, bool)
        valid = np.isfinite(zb)
        zf = np.where(valid, zb, -1e9)
        for dy, dx in ((0, 1), (1, 0)):
            z2 = np.roll(zf, (-dy, -dx), (0, 1))
            z0 = np.roll(zf, (dy, dx), (0, 1))
            n2 = np.roll(nb, (-dy, -dx), (0, 1))
            i2 = np.roll(ib, (-dy, -dx), (0, 1))
            v2 = np.roll(valid, (-dy, -dx), (0, 1))
            # Tweede afgeleide: een schuin vlak geeft geen rand, een sprong in diepte wel
            dz = np.abs(z2 - 2 * zf + z0) > 0.4
            dn = (nb * n2).sum(-1) < 0.9
            di = ib != i2
            e |= (valid | v2) & ((valid != v2) | dz | dn | di)
        return e

    def render(self, path, elev=25, azim=-55, size=(1400, 1000), title=None, labels=(), margin=0.08):
        R = view_matrix(elev, azim)
        allp = np.vstack([v @ R.T for v, *_ in self.parts])
        lo, hi = allp.min(0), allp.max(0)
        w, h = size
        top = 70 if title else 10
        scale = min(w * (1 - 2 * margin) / (hi[0] - lo[0]), (h - top) * (1 - 2 * margin) / (hi[1] - lo[1]))
        off = np.array([(lo[0] + hi[0]) / 2 - w / 2 / scale, (lo[1] + hi[1]) / 2 - (h - top) / 2 / scale])

        opaque = [(i, p) for i, p in enumerate(self.parts) if p[3] >= 1.0]
        ghost = [(i, p) for i, p in enumerate(self.parts) if p[3] < 1.0]
        zb, cb, nb, ib = self._layer(opaque, R, scale, off, size)
        img = cb.copy()
        img[self._edges(zb, nb, ib)] *= 0.25
        if ghost:
            gz, gc, gn, gi = self._layer(ghost, R, scale, off, size)
            a = max(p[3] for _, p in ghost)
            front = np.isfinite(gz) & (gz > zb)
            img[front] = img[front] * (1 - a) + gc[front] * a
            ge = self._edges(gz, gn, gi) & front
            img[ge] *= 0.55
        im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
        if title:
            # Ruimte voor de titel bovenaan
            canvas = Image.new('RGB', (w, h + 0), 'white')
            canvas.paste(im.crop((0, 0, w, h - top)), (0, top))
            im = canvas
        d = ImageDraw.Draw(im)
        if title:
            d.text((w / 2, 18), title, fill=(20, 20, 20), font=_font(34), anchor='ma')
        f = _font(26)
        for (x, y, z, text) in labels:
            p = np.array([x, y, z]) @ R.T
            sx = (p[0] - off[0]) * scale
            sy = h - (p[1] - off[1]) * scale + (top if title else 0)
            bb = d.textbbox((sx, sy), text, font=f, anchor='mm')
            d.rounded_rectangle((bb[0] - 8, bb[1] - 5, bb[2] + 8, bb[3] + 5), 6, fill=(255, 246, 190),
                                outline=(120, 120, 120), width=2)
            d.text((sx, sy), text, fill=(15, 15, 15), font=f, anchor='mm')
        im = im.crop(im.convert('L').point(lambda v: 255 if v < 250 else 0).getbbox() or (0, 0, w, h))
        pad = Image.new('RGB', (im.width + 40, im.height + 40), 'white')
        pad.paste(im, (20, 20))
        pad.save(path)
