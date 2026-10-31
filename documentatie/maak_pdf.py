"""
Zet HANDLEIDING.md (met afbeeldingen uit img/) om naar Muziekbox-handleiding.pdf.
Gebruik: python maak_pdf.py      (vereist: pip install reportlab pillow)
"""
import datetime
import os
import re

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, Preformatted, Spacer,
                                Table, TableStyle)
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate
from reportlab.platypus.frames import Frame
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'HANDLEIDING.md')
OUT = os.path.join(HERE, 'Muziekbox-handleiding.pdf')

FONTS = r'C:\Windows\Fonts'
pdfmetrics.registerFont(TTFont('Body', os.path.join(FONTS, 'arial.ttf')))
pdfmetrics.registerFont(TTFont('Body-Bold', os.path.join(FONTS, 'arialbd.ttf')))
pdfmetrics.registerFont(TTFont('Body-Italic', os.path.join(FONTS, 'ariali.ttf')))
pdfmetrics.registerFont(TTFont('Mono', os.path.join(FONTS, 'consola.ttf')))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='Body-Bold', italic='Body-Italic', boldItalic='Body-Bold')

ACCENT = colors.HexColor('#1d4ed8')
PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

S = {
    'title': ParagraphStyle('title', fontName='Body-Bold', fontSize=30, leading=36, alignment=TA_CENTER,
                            textColor=colors.HexColor('#111111')),
    'subtitle': ParagraphStyle('subtitle', fontName='Body', fontSize=13, leading=18, alignment=TA_CENTER,
                               textColor=colors.HexColor('#555555')),
    'h1': ParagraphStyle('h1', fontName='Body-Bold', fontSize=20, leading=25, spaceBefore=6, spaceAfter=8,
                         textColor=ACCENT),
    'h2': ParagraphStyle('h2', fontName='Body-Bold', fontSize=16, leading=20, spaceBefore=10, spaceAfter=6,
                         textColor=ACCENT),
    'h3': ParagraphStyle('h3', fontName='Body-Bold', fontSize=12.5, leading=16, spaceBefore=8, spaceAfter=4,
                         textColor=colors.HexColor('#1f2937')),
    'body': ParagraphStyle('body', fontName='Body', fontSize=10, leading=14, spaceAfter=5),
    'bullet': ParagraphStyle('bullet', fontName='Body', fontSize=10, leading=14, leftIndent=14, bulletIndent=3,
                             spaceAfter=2),
    'cell': ParagraphStyle('cell', fontName='Body', fontSize=9, leading=12),
    'cellh': ParagraphStyle('cellh', fontName='Body-Bold', fontSize=9, leading=12, textColor=colors.white),
    'code': ParagraphStyle('code', fontName='Mono', fontSize=7.4, leading=10.5),
    'note': ParagraphStyle('note', fontName='Body', fontSize=9.5, leading=13),
    'caption': ParagraphStyle('caption', fontName='Body-Italic', fontSize=8.5, leading=11, alignment=TA_CENTER,
                              textColor=colors.HexColor('#666666'), spaceAfter=8),
    'toc1': ParagraphStyle('toc1', fontName='Body-Bold', fontSize=10.5, leading=15, leftIndent=6),
    'toc2': ParagraphStyle('toc2', fontName='Body', fontSize=8.5, leading=10.5, leftIndent=22,
                           textColor=colors.HexColor('#444444')),
}


def inline(text):
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`([^`]+)`', r'<font name="Mono" size="9">\1</font>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<link href="\2" color="#1d4ed8">\1</link>', text)
    return text


def image(path, caption, max_h=100 * mm):
    full = os.path.join(HERE, path)
    with PILImage.open(full) as im:
        w, h = im.size
    scale = min(CONTENT_W / w, max_h / h)
    img = Image(full, width=w * scale, height=h * scale)
    # De titel staat al in de afbeelding zelf; alleen wat witruimte eronder
    return KeepTogether([img, Spacer(1, 6)])


def table(rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r':?-+:?', c) for c in r)]
    ncol = max(len(r) for r in cells)
    lens = [max(len(r[i]) if i < len(r) else 0 for r in cells) for i in range(ncol)]
    lens = [min(max(n, 6), 70) for n in lens]
    widths = [CONTENT_W * n / sum(lens) for n in lens]
    data = [[Paragraph(inline(c), S['cellh'] if ri == 0 else S['cell']) for c in r] + [''] * (ncol - len(r))
            for ri, r in enumerate(cells)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d1d5db')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return [t, Spacer(1, 6)]


def boxed(flowable, bg, border):
    t = Table([[flowable]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), bg), ('BOX', (0, 0), (-1, -1), 0.6, border),
                           ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                           ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    return [t, Spacer(1, 6)]


def parse(md):
    lines = md.splitlines()
    story, i = [], 0
    title = None
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s or s == '---':
            i += 1
            continue
        if s.startswith('```'):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('```'):
                j += 1
            code = '\n'.join(lines[i + 1:j])
            story += boxed(Preformatted(code, S['code'], maxLineLength=118, newLineChars=''),
                           colors.HexColor('#f3f4f6'), colors.HexColor('#d1d5db'))
            i = j + 1
            continue
        if s.startswith('# '):
            title = s[2:]
            i += 1
            continue
        if s.startswith('## '):
            story.append(CondPageBreak(70 * mm))
            p = Paragraph(inline(s[3:]), S['h2'])
            p.toc_level = 0
            story.append(p)
            i += 1
            continue
        if s.startswith('### '):
            story.append(CondPageBreak(40 * mm))
            p = Paragraph(inline(s[4:]), S['h3'])
            p.toc_level = 1
            story.append(p)
            i += 1
            continue
        m = re.match(r'!\[(.*?)\]\((.*?)\)', s)
        if m:
            story.append(image(m.group(2), m.group(1)))
            i += 1
            continue
        if s.startswith('|'):
            j = i
            while j < len(lines) and lines[j].strip().startswith('|'):
                j += 1
            story += table(lines[i:j])
            i = j
            continue
        if s.startswith('>'):
            j = i
            parts = []
            while j < len(lines) and lines[j].strip().startswith('>'):
                parts.append(lines[j].strip()[1:].strip())
                j += 1
            story += boxed(Paragraph(inline(' '.join(parts)), S['note']), colors.HexColor('#fff7d6'),
                           colors.HexColor('#e0b100'))
            i = j
            continue
        m = re.match(r'(\d+)\.\s+(.*)', s)
        if m:
            story.append(Paragraph(inline(m.group(2)), S['bullet'], bulletText=f'{m.group(1)}.'))
            i += 1
            continue
        if s.startswith('- '):
            story.append(Paragraph(inline(s[2:]), S['bullet'], bulletText='•'))
            i += 1
            continue
        # gewone alinea (aaneengesloten regels)
        j = i
        para = []
        while j < len(lines) and lines[j].strip() and not re.match(r'(#|\||>|-\s|\d+\.\s|!\[|```)', lines[j].strip()):
            para.append(lines[j].strip())
            j += 1
        story.append(Paragraph(inline(' '.join(para)), S['body']))
        i = j
    return title, story


class Doc(BaseDocTemplate):
    def __init__(self, path, title):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN,
                         bottomMargin=MARGIN, title=title, author='Muziekbox', subject='Bouwhandleiding')
        frame = Frame(MARGIN, MARGIN, CONTENT_W, PAGE_H - 2 * MARGIN, id='f')
        self.doc_title = title
        self.addPageTemplates([PageTemplate('cover', [frame]),
                               PageTemplate('page', [frame], onPage=self.decorate)])

    def decorate(self, canv, doc):
        canv.saveState()
        canv.setFont('Body', 8)
        canv.setFillColor(colors.HexColor('#777777'))
        canv.drawString(MARGIN, 10 * mm, self.doc_title)
        canv.drawRightString(PAGE_W - MARGIN, 10 * mm, f'pagina {doc.page}')
        canv.setStrokeColor(colors.HexColor('#dddddd'))
        canv.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
        canv.restoreState()

    def afterFlowable(self, flowable):
        level = getattr(flowable, 'toc_level', None)
        if level is not None:
            text = flowable.getPlainText()
            key = f'h{self.seq.nextf("heading")}'
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
            self.notify('TOCEntry', (level, text, self.page, key))


def main():
    with open(SRC, encoding='utf-8') as f:
        md = f.read()
    title, body = parse(md)

    # Voorblad: titel, eerste afbeelding (eindresultaat) en datum
    first_img = next((x for x in body if isinstance(x, KeepTogether)), None)
    body.remove(first_img)
    intro = []
    while body and isinstance(body[0], Paragraph) and getattr(body[0], 'toc_level', None) is None:
        intro.append(body.pop(0))
    from reportlab.platypus.doctemplate import NextPageTemplate
    cover = [Spacer(1, 25 * mm), Paragraph(title, S['title']), Spacer(1, 6 * mm),
             Paragraph('Phoniebox met Spotify, NFC-kaarten en PiSugar-accu', S['subtitle']),
             Spacer(1, 10 * mm), first_img, Spacer(1, 4 * mm)] + intro + [
        Spacer(1, 8 * mm),
        Paragraph(f'Versie {datetime.date.today():%d-%m-%Y}', S['subtitle']),
        NextPageTemplate('page'), PageBreak()]

    toc = TableOfContents()
    toc.levelStyles = [S['toc1'], S['toc2']]
    toc_page = [Paragraph('Inhoud', S['h1']), toc, PageBreak()]

    doc = Doc(OUT, title)
    doc.multiBuild(cover + toc_page + body)
    print('PDF gemaakt:', OUT)


if __name__ == '__main__':
    main()
