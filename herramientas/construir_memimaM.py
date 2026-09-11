"""
construir_memimaM.py — Construye MemimaM / Mestra1M / Mestra2M: la familia Memima
con mayúsculas habituales (de imprenta), tomadas de Abecedario (GPL-2).

Necesita en la misma carpeta: Memima.ttf, Mestra1_MeMimaPautada_.TTF,
Mestra2_MeMimaPuntejada_.TTF (originales, uso escolar privado) y Abecedario.ttf
(repositorio, carpeta fuentes/). Dependencias: fonttools, pillow, numpy,
scikit-image, shapely.

Qué hace con cada mayúscula de Abecedario:
  · la escala a la altura de las mayúsculas de Memima y afina el trazo a su grosor;
  · MemimaM: la letra tal cual; Mestra1M: la letra + las dos rayas de la pauta;
  · Mestra2M: calcula la línea central de la letra y la dibuja con el mismo patrón
    de repaso de Mestra2 (pares de marcas), + las dos rayas de la pauta.
Las minúsculas, signos y pauta de Memima no se tocan.
El resultado es de uso privado: NO se publica (va codificado en el Proyecto).
"""
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from PIL import Image, ImageDraw
import numpy as np, math
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from skimage.morphology import skeletonize

MAYUS = "ABCDEFGHIJKLMNOPQRSTUVWXYZÑÁÉÍÓÚÜÀÈÌÒÙÂÊÎÔÛÄËÏÖÇ"
ESCALA, IZQ, DER = 0.945, 40, 110           # tamaño y márgenes de la mayúscula
PAUTA1 = [(0, 15), (260, 275)]              # rayas de Mestra1
PAUTA2 = [(0, 15), (259, 274)]              # rayas de Mestra2
MARCA = [(18,12),(12,17),(9,17),(4,17),(0,10),(0,8),(0,4),(6,0),(9,0),(18,0),(18,8)]  # marca de Mestra2
PASO_PAR, PERIODO = 18, 62                  # dos marcas juntas cada 62 unidades
ADELGAZAR = 5.5                             # Abecedario ~31 u de trazo; Memima ~20 u

def contorno_fuente(cp, src, sgs):
    """Grabación de la mayúscula de Abecedario ya escalada y colocada."""
    sg = sgs[src.getBestCmap()[cp]]
    bp = BoundsPen(sgs); sg.draw(bp)
    xmin, ymin, xmax, ymax = bp.bounds
    rec = RecordingPen()
    sg.draw(TransformPen(rec, (ESCALA, 0, 0, ESCALA, IZQ - xmin*ESCALA, 0)))
    adv = int(round((xmax - xmin)*ESCALA + IZQ + DER))
    return rec, adv

def poligonos(rec):
    """Convierte la grabación en polígonos (curvas aplanadas) para rasterizar."""
    polys, cur = [], []
    def q(p0, p1, p2, n=8):
        return [((1-t)**2*p0[0]+2*(1-t)*t*p1[0]+t*t*p2[0], (1-t)**2*p0[1]+2*(1-t)*t*p1[1]+t*t*p2[1]) for t in [i/n for i in range(1,n+1)]]
    for op, args in rec.value:
        if op == "moveTo": cur = [args[0]]
        elif op == "lineTo": cur.append(args[0])
        elif op == "qCurveTo":
            pts = list(args); p0 = cur[-1]
            for i in range(len(pts)-1):
                c = pts[i]; e = pts[i+1] if i == len(pts)-2 else ((pts[i][0]+pts[i+1][0])/2, (pts[i][1]+pts[i+1][1])/2)
                cur += q(p0, c, e); p0 = e
        elif op == "curveTo":
            p0 = cur[-1]; c1, c2, e = args
            for t in [i/10 for i in range(1, 11)]:
                cur.append(((1-t)**3*p0[0]+3*(1-t)**2*t*c1[0]+3*(1-t)*t*t*c2[0]+t**3*e[0],
                            (1-t)**3*p0[1]+3*(1-t)**2*t*c1[1]+3*(1-t)*t*t*c2[1]+t**3*e[1]))
        elif op in ("closePath", "endPath"):
            if len(cur) > 2: polys.append(cur)
            cur = []
    return polys


def adelgazado(polys):
    """Geometría de la letra con el trazo afinado al grosor de Memima."""
    geo = None
    for pl in polys:
        p = Polygon(pl).buffer(0)
        geo = p if geo is None else geo.symmetric_difference(p)
    return geo.buffer(-ADELGAZAR, join_style="round", quad_segs=4)

def dibujar_geo(geo, pen):
    for pol in getattr(geo, "geoms", [geo]):
        if pol.is_empty: continue
        pol = orient(pol, sign=-1.0)          # exterior en sentido horario (TrueType)
        for anillo in [pol.exterior] + list(pol.interiors):
            pts = [(int(round(x)), int(round(y))) for x, y in list(anillo.coords)[:-1]]
            limpio = [p for i, p in enumerate(pts) if p != pts[i-1]]
            if len(limpio) < 3: continue
            pen.moveTo(limpio[0]); [pen.lineTo(p) for p in limpio[1:]]; pen.closePath()

def trazos(polys, esc=3):
    """Esqueleto (línea central) de la letra como lista de caminos ordenados."""
    xs = [p[0] for pl in polys for p in pl]; ys = [p[1] for pl in polys for p in pl]
    x0, y0 = min(xs) - 10, min(ys) - 10; W = int((max(xs) - x0 + 10)*esc); H = int((max(ys) - y0 + 10)*esc)
    im = Image.new("1", (W, H), 0); d = ImageDraw.Draw(im)
    for pl in polys:   # regla par-impar: dibujar con XOR
        m = Image.new("1", (W, H), 0); ImageDraw.Draw(m).polygon([((x-x0)*esc, H-(y-y0)*esc) for x, y in pl], fill=1)
        im = Image.fromarray(np.logical_xor(np.array(im), np.array(m)))
    arr = np.ascontiguousarray(np.pad(np.array(im, dtype=np.uint8) > 0, 2), dtype=bool)
    sk = skeletonize(arr)[2:-2, 2:-2]
    S = set(zip(*np.nonzero(sk)))
    def vec(p): return [(p[0]+a, p[1]+b) for a in (-1,0,1) for b in (-1,0,1) if (a or b) and (p[0]+a, p[1]+b) in S]
    grado = {p: len(vec(p)) for p in S}
    nodos = {p for p in S if grado[p] != 2}
    usados, caminos = set(), []
    def andar(a, b):
        cam = [a, b]; usados.add(frozenset((a, b)))
        while cam[-1] not in nodos:
            sig = [n for n in vec(cam[-1]) if frozenset((cam[-1], n)) not in usados and n != cam[-2]]
            if not sig: break
            usados.add(frozenset((cam[-1], sig[0]))); cam.append(sig[0])
            if cam[-1] == cam[0]: break
        return cam
    for n in nodos:
        for m in vec(n):
            if frozenset((n, m)) not in usados: caminos.append(andar(n, m))
    for p in S:   # bucles cerrados sin nodos (O, D…)
        for m in vec(p):
            if frozenset((p, m)) not in usados: caminos.append(andar(p, m))
    return [[(c/esc + x0, (H - r)/esc + y0) for r, c in cam] for cam in caminos if len(cam) > 4]

def marcas_en(camino):
    """Pares de marcas a lo largo de un camino (patrón de Mestra2)."""
    # suavizado
    P = np.array(camino, float)
    if len(P) > 7:
        k = 3; P = np.array([P[max(0,i-k):i+k+1].mean(0) for i in range(len(P))])
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    L = seg[-1]; res = []
    if L < 12: return res
    n = max(1, int(round(L / PERIODO)))
    for i in range(n):
        s0 = (L - PASO_PAR) * (i + 0.5) / n
        for s in (s0, s0 + PASO_PAR):
            s = min(s, L); j = np.searchsorted(seg, s)
            j = min(max(j, 1), len(seg)-1); t = (s - seg[j-1]) / max(seg[j]-seg[j-1], 1e-9)
            res.append(tuple(P[j-1] + t*(P[j]-P[j-1])))
    return res

def construir(base, salida, modo):
    src = TTFont("Abecedario.ttf"); sgs = src.getGlyphSet()
    dst = TTFont(base); dcmap = dst.getBestCmap(); glyf = dst["glyf"]; hmtx = dst["hmtx"]
    for ch in MAYUS:
        cp = ord(ch)
        if cp not in src.getBestCmap() or cp not in dcmap: continue
        rec, adv = contorno_fuente(cp, src, sgs)
        pen = TTGlyphPen(None)
        if modo == "repaso":
            puntos = []
            for cam in trazos(poligonos(rec)): puntos += marcas_en(cam)
            # quitar marcas casi superpuestas (cruces)
            final = []
            for p in puntos:
                if all(math.dist(p, q) > 11 for q in final): final.append(p)
            for (cx, cy) in final:
                pts = [(int(round(cx - 9 + x)), int(round(cy - 8.5 + y))) for x, y in MARCA]
                pen.moveTo(pts[0]); [pen.lineTo(p) for p in pts[1:]]; pen.closePath()
        else:
            dibujar_geo(adelgazado(poligonos(rec)), pen)
        if modo in ("pauta", "repaso"):
            for y0, y1 in (PAUTA1 if modo == "pauta" else PAUTA2):
                pen.moveTo((-9, y0)); pen.lineTo((-9, y1)); pen.lineTo((adv+21, y1)); pen.lineTo((adv+21, y0)); pen.closePath()
        g = pen.glyph(); glyf[dcmap[cp]] = g; g.recalcBounds(glyf)
        hmtx[dcmap[cp]] = (adv, g.xMin if g.numberOfContours else 0)
    for rec in dst["name"].names:
        if rec.nameID in (1, 3, 4, 6):
            s = rec.toUnicode()
            rec.string = (s.replace(" ", "") + "M")[:63] if rec.nameID == 6 else s + " M"
    dst.save(salida)

if __name__ == "__main__":
    construir("Memima.ttf", "MemimaM.ttf", "normal")
    construir("Mestra1_MeMimaPautada_.TTF", "Mestra1M.ttf", "pauta")
    construir("Mestra2_MeMimaPuntejada_.TTF", "Mestra2M.ttf", "repaso")
    print("construidas: MemimaM.ttf, Mestra1M.ttf, Mestra2M.ttf")
