#!/usr/bin/env python3
"""letras_escolar.py — Sustituye la «s» y la «x» minúsculas de la familia Memima
por las formas de Escolar1 (Escolar_G.TTF).

La s y la x de Memima tienen formas caligráficas poco reconocibles para quien
empieza a leer. Estas vienen de Escolar1, que es la forma que ha elegido la
docente, adaptadas al cuerpo de Memima:

  · se escalan a la altura x de Memima (260 unidades);
  · se vuelven monolínea, con el grosor de Memima (trazo de 21), tomando la
    línea central de la letra y engrosándola con discos;
  · se bajan las colas de entrada y de salida a la altura a la que ligan todas
    las letras de Memima (120), para que la escritura siga enlazada.

Cada fuente recibe su versión, igual que en zeta.py:
  MemimaM   (modelo, lectura) → la letra sola.
  Mestra1M  (renglón)         → la letra + las dos rayas de la pauta.
  Mestra2M  (repaso)          → la letra en rayitas + las dos rayas de la pauta.

Uso:  python3 letras_escolar.py MemimaM.ttf Mestra1M.ttf Mestra2M.ttf
      (reescribe los tres archivos; necesita Escolar_G.TTF en la misma carpeta)

Dependencias: fonttools, pillow, numpy, scikit-image, skia-pathops.
"""
import math, sys
import numpy as np
from PIL import Image, ImageDraw
from skimage.morphology import skeletonize
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
import pathops

ORIGEN   = 'Escolar_G.TTF'   # familia Escolar1
LETRAS   = 'sx'
XH_ORIG  = 336.0   # altura x de Escolar1 (alto de la n)
XH_DEST  = 260.0   # altura x de Memima
LIGADO   = 120.0   # altura a la que ligan las letras de Memima
RADIO    = 10.5    # medio grosor del trazo de Memima
COLA     = 95.0    # longitud de la cola que se corrige al bajar el ligado
# La s de Escolar1 está pensada para un ligado más alto (0,63 de la altura x,
# frente a 0,46 en Memima). Al bajar la entrada, el bucle de abajo se cierra
# contra ella. Estos dos retoques le devuelven el aire que tiene en Escolar1:
RECORTE_S = 50.0   # se acorta la punta libre del bucle inferior, que si no
                   # queda casi pegada a la ligadura de entrada
BAJA_S    = 0.0    # (sin bajarla: con el recorte basta)
PAUTA1   = [(0, 15), (260, 275)]   # rayas de Mestra1M
PAUTA2   = [(0, 15), (259, 274)]   # rayas de Mestra2M
BANDA    = (-18, 30)               # la pauta sobresale así por cada lado
MARCA    = [(18,12),(12,17),(9,17),(4,17),(0,10),(0,8),(0,4),(6,0),(9,0),(18,0),(18,8)]
PASO_PAR, PERIODO = 18, 62         # pares de rayitas del trazo de repaso


# ---------------------------------------------------------------- contorno
def poligonos(rec):
    """Grabación → polígonos (curvas aplanadas)."""
    polys, cur = [], []
    def q(p0, p1, p2, n=8):
        return [((1-t)**2*p0[0]+2*(1-t)*t*p1[0]+t*t*p2[0],
                 (1-t)**2*p0[1]+2*(1-t)*t*p1[1]+t*t*p2[1]) for t in [i/n for i in range(1, n+1)]]
    for op, args in rec.value:
        if op == "moveTo": cur = [args[0]]
        elif op == "lineTo": cur.append(args[0])
        elif op == "qCurveTo":
            pts = list(args); p0 = cur[-1]
            for i in range(len(pts)-1):
                c = pts[i]
                e = pts[i+1] if i == len(pts)-2 else ((pts[i][0]+pts[i+1][0])/2, (pts[i][1]+pts[i+1][1])/2)
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


def trazos(polys, esc=3, espuela=30.0):
    """Línea central de la letra, como lista de caminos ordenados.

    El esqueleto de una punta redonda se abre en una Y y deja dos ramitas
    falsas; se podan antes de nada (`espuela`, en unidades de la fuente), para
    que el extremo de cada trazo sea un punto único y la cola se pueda ajustar.
    """
    xs = [p[0] for pl in polys for p in pl]; ys = [p[1] for pl in polys for p in pl]
    x0, y0 = min(xs) - 10, min(ys) - 10
    W = int((max(xs) - x0 + 10)*esc); H = int((max(ys) - y0 + 10)*esc)
    im = Image.new("1", (W, H), 0)
    for pl in polys:                      # regla par-impar
        m = Image.new("1", (W, H), 0)
        ImageDraw.Draw(m).polygon([((x-x0)*esc, H-(y-y0)*esc) for x, y in pl], fill=1)
        im = Image.fromarray(np.logical_xor(np.array(im), np.array(m)))
    arr = np.ascontiguousarray(np.pad(np.array(im, dtype=np.uint8) > 0, 2), dtype=bool)
    sk = skeletonize(arr)[2:-2, 2:-2]
    S = set(zip(*np.nonzero(sk)))

    def vec(p): return [(p[0]+a, p[1]+b) for a in (-1,0,1) for b in (-1,0,1)
                        if (a or b) and (p[0]+a, p[1]+b) in S]

    # --- poda de ramitas falsas
    while True:
        extremos = [p for p in S if len(vec(p)) == 1]
        fuera = set()
        for e in extremos:
            rama = [e]; act = e
            while True:
                sig = [n for n in vec(act) if n not in rama]
                if len(sig) != 1 or len(vec(sig[0])) > 2: break
                rama.append(sig[0]); act = sig[0]
            nodo = [n for n in vec(act) if n not in rama]
            if nodo and len(rama)/esc < espuela: fuera.update(rama)
        if not fuera: break
        S -= fuera

    nodos = {p for p in S if len(vec(p)) != 2}
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
    for p in S:
        for m in vec(p):
            if frozenset((p, m)) not in usados: caminos.append(andar(p, m))
    return [[(c/esc + x0, (H - r)/esc + y0) for r, c in cam] for cam in caminos if len(cam) > 4]


# ------------------------------------------------------------------ ajuste
def suavizar(cam, k=3):
    P = np.array(cam, float)
    if len(P) <= 2*k + 1: return P
    return np.array([P[max(0, i-k):i+k+1].mean(0) for i in range(len(P))])


def bajar_cola(P, desde_inicio, dy):
    """Corrige dy en el extremo indicado, repartido a lo largo de COLA."""
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    s = seg if desde_inicio else seg[-1] - seg
    w = np.clip(1 - s/COLA, 0, 1)
    w = w*w*(3 - 2*w)                      # suavizado: pendiente nula al soltar
    Q = P.copy(); Q[:, 1] += dy*w
    return Q


def abrir_bucle(P, desde_inicio):
    """Acorta y baja la punta libre del bucle inferior de la s."""
    Q = P[::-1] if desde_inicio else P          # trabajar con la punta al final
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]
    Q = Q[seg <= seg[-1] - RECORTE_S]
    if len(Q) > 2 and BAJA_S:
        s2 = np.r_[0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]
        w = np.clip(1 - (s2[-1] - s2)/70.0, 0, 1); w = w*w*(3 - 2*w)
        Q = Q.copy(); Q[:, 1] -= BAJA_S*w
    return Q[::-1] if desde_inicio else Q


def centrales(ch):
    """Líneas centrales de la letra, ya escaladas y con las colas a la altura de ligado."""
    src = TTFont(ORIGEN); gs = src.getGlyphSet()
    rec = RecordingPen(); gs[src.getBestCmap()[ord(ch)]].draw(rec)
    k = XH_DEST/XH_ORIG
    cams = [suavizar(c)*k for c in trazos(poligonos(rec))]
    # puntas reales: extremos que no comparten sitio con ningún otro (los que sí
    # lo comparten son nudos donde se cruzan o se juntan dos trazos)
    todos = [(i, j, tuple(cams[i][j])) for i, c in enumerate(cams) for j in (0, -1)]
    puntas = [(i, j) for i, j, p in todos
              if all(math.hypot(p[0]-q[0], p[1]-q[1]) > 5 for a, b, q in todos if (a, b) != (i, j))]
    ent = min(puntas, key=lambda e: cams[e[0]][e[1]][0])
    sal = max(puntas, key=lambda e: cams[e[0]][e[1]][0])
    for i, j in (ent, sal):
        cams[i] = bajar_cola(cams[i], j == 0, LIGADO - cams[i][j][1])
    if ch == 's':
        cola = [e for e in puntas if e not in (ent, sal)]
        if cola: cams[cola[0][0]] = abrir_bucle(cams[cola[0][0]], cola[0][1] == 0)
    dx = cams[ent[0]][ent[1]][0]
    cams = [c - [dx, 0] for c in cams]
    return cams, float(cams[sal[0]][sal[1]][0])


# ------------------------------------------------------------------ dibujo
def muestrear(P, paso=3.0):
    out = [P[0]]; resto = 0.0
    for p, q in zip(P, P[1:]):
        dx, dy = q[0]-p[0], q[1]-p[1]; L = math.hypot(dx, dy)
        if L == 0: continue
        d = paso - resto
        while d <= L:
            out.append((p[0] + dx*d/L, p[1] + dy*d/L)); d += paso
        resto = L - (d - paso)
    out.append(tuple(P[-1])); return out


def horario(pts):
    s = sum(pts[i][0]*pts[(i+1) % len(pts)][1] - pts[(i+1) % len(pts)][0]*pts[i][1] for i in range(len(pts)))
    return pts if s < 0 else pts[::-1]


def trazo_grueso(cams):
    """Une discos a lo largo de las líneas centrales: esquinas y puntas redondas."""
    caminos = []
    for cam in cams:
        for cx, cy in muestrear(cam):
            c = horario([(cx + RADIO*math.cos(2*math.pi*i/24), cy + RADIO*math.sin(2*math.pi*i/24))
                         for i in range(24)])
            p = pathops.Path(); pen = p.getPen()
            pen.moveTo(c[0])
            for q in c[1:]: pen.lineTo(q)
            pen.closePath(); caminos.append(p)
    final = pathops.Path()
    pathops.union(caminos, final.getPen(), clockwise=True)
    return final


def marcas(cam):
    """Pares de rayitas repartidos a lo largo de una línea central."""
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(cam, axis=0).T))]
    L = seg[-1]
    if L < 12: return []
    n = max(1, int(round(L/PERIODO))); res = []
    for i in range(n):
        s0 = (L - PASO_PAR)*(i + 0.5)/n
        for s in (s0, s0 + PASO_PAR):
            s = min(s, L); j = int(np.searchsorted(seg, s)); j = min(max(j, 1), len(seg)-1)
            t = (s - seg[j-1])/max(seg[j] - seg[j-1], 1e-9)
            res.append(tuple(cam[j-1] + t*(cam[j] - cam[j-1])))
    return res


def injertar(ruta, modo, destino=None):
    font = TTFont(ruta); glyf = font['glyf']; cmap = font.getBestCmap()
    for ch in LETRAS:
        cams, adv = centrales(ch)
        adv = int(round(adv))
        pen = TTGlyphPen(font.getGlyphSet())
        if modo == 'repaso':
            puntos = []
            for cam in cams: puntos += marcas(cam)
            final = []
            for p in puntos:
                if all(math.hypot(p[0]-q[0], p[1]-q[1]) > 11 for q in final): final.append(p)
            for cx, cy in final:
                pts = [(int(round(cx - 9 + x)), int(round(cy - 8.5 + y))) for x, y in MARCA]
                pen.moveTo(pts[0])
                for q in pts[1:]: pen.lineTo(q)
                pen.closePath()
        else:
            trazo_grueso(cams).draw(pen)
        bandas = {'pauta': PAUTA1, 'repaso': PAUTA2}.get(modo)
        if bandas:
            for y0, y1 in bandas:
                c = [(BANDA[0], y0), (BANDA[0], y1), (adv + BANDA[1], y1), (adv + BANDA[1], y0)]
                pen.moveTo(c[0])
                for q in c[1:]: pen.lineTo(q)
                pen.closePath()
        g = pen.glyph(); gn = cmap[ord(ch)]
        glyf[gn] = g; g.recalcBounds(glyf)
        font['hmtx'][gn] = (adv, g.xMin if g.numberOfContours else 0)
        print(f'  {ch}: avance {adv}')
    font.save(destino or ruta)
    print(f'{destino or ruta}: s y x sustituidas ({modo})')


MODOS = {'MemimaM': 'normal', 'Mestra1M': 'pauta', 'Mestra2M': 'repaso'}

if __name__ == '__main__':
    for ruta in sys.argv[1:]:
        nombre = ruta.split('/')[-1].split('.')[0]
        modo = MODOS.get(nombre)
        if modo is None:
            sys.exit(f'No sé qué versión poner en «{ruta}»: esperaba uno de {", ".join(MODOS)}.')
        injertar(ruta, modo)
