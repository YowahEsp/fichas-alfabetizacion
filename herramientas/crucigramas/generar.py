"""Generador de cruzadas con pictogramas (formato aprobado CRUCIGRAMA_L45_01).

Uso:
  python3 generar.py <carpeta> [--n 25] [--semilla 2026] [--leccion L] [--max-usos 4]
                     [--fijas fijas.json] [--extra extra.txt] [--procesos 8]

  <carpeta>   carpeta de trabajo donde ya se ha ejecutado pictos.py (pictos/ y aspectos.json).
  --n         número de cruzadas (cr-01 … cr-NN).
  --leccion   solo palabras admitidas en esa lección de Palau (usa validador_grafemas.py del
              repositorio). Sin ella, cualquier palabra de la lista (nivel L72).
  --max-usos  veces que puede salir cada palabra en todo el repertorio.
  --fijas     JSON con una lista de listas de 18 palabras: una por cruzada, se respetan tal cual.
  --extra     palabras añadidas a la lista, una por línea: «palabra id_arasaac». Su pictograma
              debe revisarse a mano (ver lista.py) y descargarse con pictos.py --extra.

Escribe <carpeta>/cr_XX.json con todo lo necesario para montar.py y un resumen en pantalla.

Algoritmo:
  1. Elegir 18 palabras sin pares en conflicto, prefiriendo las menos usadas.
  2. Generar miles de rejillas: colocación voraz desde la palabra más larga, cada palabra donde
     más cruces tenga y menos crezca el rectángulo; cruces solo en letra idéntica sin tilde;
     se descartan las que dejan huecos cerrados o casillas de número en conflicto.
  3. Para cada rejilla, la casilla máxima (pasos de 0,25 mm) con la que caben la rejilla y los
     18 dibujos de 24 mm (2 mm de aire) en la zona de 281 × 177 mm.
  4. Dibujos en los mayores huecos libres (24–32 mm), asignados por cercanía a su palabra
     (asignación húngara); número del dibujo dentro de su hueco.
  5. Si la casilla no llega a 14 mm, más rondas; si sigue por debajo de 13 mm, se cambian las
     dos palabras más largas por otras cortas (salvo con --fijas).
"""
import argparse, json, os, random, sys
import numpy as np
from multiprocessing import Pool as MPool
from scipy.optimize import linear_sum_assignment
from lista import PALABRAS, nombre, en_conflicto, cargar_extra

RW, RH = 281, 177          # zona de trabajo en mm (A4 apaisado menos márgenes y enunciado)
GAP = 2                    # aire mínimo entre dibujos, casillas y números (mm)
NPAL = 18                  # palabras por cruzada
PMIN, PMAX = 24, 32        # lado del hueco de cada dibujo (mm)
ACC = set('áéíóú')
ASP = {}                   # proporciones de los dibujos (se cargan en main)

# ---------------------------------------------------------------- rejilla
class Grid:
    def __init__(self):
        self.cells, self.dirs, self.words = {}, {}, []
    def copy(self):
        g = Grid(); g.cells = dict(self.cells); g.dirs = {k: set(v) for k, v in self.dirs.items()}
        g.words = list(self.words); return g
    def can(self, w, r, c, d):
        """n.º de cruces si la palabra cabe ahí, o -1. Cruce solo en letra idéntica y sin tilde
        (la ñ solo cruza con ñ)."""
        dr, dc = (0, 1) if d == 'A' else (1, 0)
        n = len(w); cross = 0
        if (r-dr, c-dc) in self.cells or (r+dr*n, c+dc*n) in self.cells: return -1
        for i, ch in enumerate(w):
            p = (r+dr*i, c+dc*i)
            if p in self.cells:
                if d in self.dirs[p] or self.cells[p] != ch or ch in ACC: return -1
                cross += 1
            else:
                for s in (-1, 1):
                    if (p[0]+dc*s, p[1]+dr*s) in self.cells: return -1
        return cross
    def place(self, w, r, c, d):
        dr, dc = (0, 1) if d == 'A' else (1, 0)
        for i, ch in enumerate(w):
            p = (r+dr*i, c+dc*i); self.cells[p] = ch; self.dirs.setdefault(p, set()).add(d)
        self.words.append((w, r, c, d))
    def bbox(self):
        rs = [p[0] for p in self.cells]; cs = [p[1] for p in self.cells]
        for w, r, c, d in self.words:
            if d == 'A': cs.append(c-1)
            else: rs.append(r-1)
        return min(rs), max(rs), min(cs), max(cs)

def huecos_cerrados(g):
    """¿Queda algún hueco vacío rodeado de casillas por los cuatro lados? Se vería como una
    casilla (o un recuadro) más, sin serlo."""
    r0, r1, c0, c1 = g.bbox(); r0 -= 1; c0 -= 1; r1 += 1; c1 += 1
    vistos = set(); pila = [(r0, c0)]
    while pila:
        p = pila.pop()
        if p in vistos or p in g.cells or not (r0 <= p[0] <= r1 and c0 <= p[1] <= c1): continue
        vistos.add(p); r, c = p
        pila += [(r+1, c), (r-1, c), (r, c+1), (r, c-1)]
    total = (r1-r0+1)*(c1-c0+1) - len(g.cells)
    return len(vistos) < total

def labels_ok(g):
    lab = set()
    for w, r, c, d in g.words:
        p = (r, c-1) if d == 'A' else (r-1, c)
        if p in lab or p in g.cells: return False
        lab.add(p)
    return True

def build(words, rng, ratio):
    g = Grid(); ws = words[:]
    first = max(ws, key=len); ws.remove(first); g.place(first, 0, 0, 'A')
    pending = ws
    for _ in range(3):
        rest = []; rng.shuffle(pending)
        for w in pending:
            best = []
            for (pr, pc), ch in list(g.cells.items()):
                for i, wc in enumerate(w):
                    if wc != ch: continue
                    for d in 'AD':
                        r, c = (pr, pc-i) if d == 'A' else (pr-i, pc)
                        x = g.can(w, r, c, d)
                        if x < 1: continue
                        g2 = g.copy(); g2.place(w, r, c, d)
                        if not labels_ok(g2): continue
                        r0, r1, c0, c1 = g2.bbox()
                        size = max((c1-c0+1)/ratio, r1-r0+1)
                        best.append((x*2 - size*0.6 + rng.random()*1.5, r, c, d))
            if best:
                _, r, c, d = max(best); g.place(w, r, c, d)
            else: rest.append(w)
        pending = rest
        if not pending: break
    return None if pending or huecos_cerrados(g) else g

def libres(subpool, rng):
    """18 palabras del subconjunto sin pares en conflicto (una lista fija se usa tal cual)."""
    if len(subpool) == NPAL: return list(subpool)
    ws = subpool[:]; rng.shuffle(ws); sel = []
    for w in ws:
        if en_conflicto(w, sel): continue
        sel.append(w)
        if len(sel) == NPAL: return sel
    return None

def trabajo(args):
    subpool, seed, n = args
    rng = random.Random(seed); out = []
    for _ in range(n):
        sel = libres(subpool, rng)
        if not sel: continue
        g = build(sel, rng, rng.uniform(1.3, 2.2))
        if g: out.append({'words': g.words, 'bbox': g.bbox()})
    return out

# ---------------------------------------------------------------- huecos para dibujos
def obstacles(words, s, ox, oy, r0, c0):
    m = np.zeros((RH, RW), bool); cells = set()
    for w, r, c, d in words:
        dr, dc = (0, 1) if d == 'A' else (1, 0)
        for i in range(len(w)): cells.add((r+dr*i, c+dc*i))
        cells.add((r, c-1) if d == 'A' else (r-1, c))
    for r, c in cells:
        y = oy + (r-r0)*s; x = ox + (c-c0)*s
        m[int(max(0, y-GAP)):int(min(RH, np.ceil(y+s+GAP))), int(max(0, x-GAP)):int(min(RW, np.ceil(x+s+GAP)))] = True
    return m

def place_greedy(m, p, n, order):
    """¿Caben n cuadrados de lado p (con separación GAP) en la zona libre? Colocación voraz
    en el orden dado, sobre el mapa de esquinas libres (una sola suma acumulada)."""
    ii = np.pad(m.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    free = (ii[p:, p:] - ii[:-p, p:] - ii[p:, :-p] + ii[:-p, :-p]) == 0
    if order in ('col', 'colr'): free = free.T.copy()
    if order in ('rowr', 'colr'): free = free[:, ::-1].copy()
    W = free.shape[1]; R = p + GAP
    for _ in range(n):
        k = int(np.argmax(free))
        if not free.flat[k]: return False
        y, x = divmod(k, W)
        free[max(0, y-R+1):y+R, max(0, x-R+1):x+R] = False
    return True

def feasible(cand, s):
    r0, r1, c0, c1 = cand['bbox']; H = r1-r0+1; W = c1-c0+1
    gw, gh = W*s, H*s
    if gw > RW or gh > RH: return None
    for ox in sorted({0, (RW-gw)/2, RW-gw}):
        for oy in sorted({0, (RH-gh)/2, RH-gh}):
            m = obstacles(cand['words'], s, ox, oy, r0, c0)
            for order in ('row', 'col', 'rowr', 'colr'):
                if place_greedy(m, PMIN, NPAL, order): return (ox, oy)
    return None

def mejor(cands):
    """Rejilla con la casilla más grande (pasos de 0,25 mm) en la que caben los 18 dibujos.
    Se prueba cada candidata desde su tamaño máximo hacia abajo."""
    def smax(c):
        r0, r1, c0, c1 = c['bbox']; return min(RW/(c1-c0+1), RH/(r1-r0+1))
    def ok(c, s):
        r = feasible(c, s)
        if not r: return None
        try: return maquetar(s, c, *r)          # la colocación definitiva también debe caber
        except RuntimeError: return None
    cands.sort(key=smax, reverse=True); best = (0, None, None)
    for c in cands:                      # de arriba abajo: la factibilidad no es monótona en s
        q = int(np.floor(smax(c)*4))
        while q > best[0]*4:
            r = ok(c, q/4)
            if r: best = (q/4, c, r); break
            q -= 1
        if smax(c) <= best[0] + 0.25: break
    return best

def largest_square(m):
    """Mayor cuadrado libre (lado en mm) y su esquina superior izquierda (primera en orden de lectura)."""
    ii = np.pad(m.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    def free(k):
        win = ii[k:, k:] - ii[:-k, k:] - ii[k:, :-k] + ii[:-k, :-k]
        return np.argwhere(win == 0)
    lo, hi = 0, min(m.shape)
    while lo < hi:
        mid = (lo + hi + 1)//2
        if len(free(mid)): lo = mid
        else: hi = mid - 1
    if lo == 0: return 0, 0, 0
    y, x = free(lo)[0]
    return lo, int(y), int(x)

# ---------------------------------------------------------------- maquetación de un crucigrama
def maquetar(s, c, ox, oy):
    r0, r1, c0, c1 = c['bbox']
    words = sorted(c['words'], key=lambda w: (w[1], w[2], w[3]))     # numeración en orden de lectura
    def cxy(r, cc): return ox + (cc-c0)*s, oy + (r-r0)*s
    m = obstacles(words, s, ox, oy, r0, c0); spots = []
    for _ in range(NPAL):
        k, y, x = largest_square(m); p = min(k, PMAX)
        if p < PMIN: raise RuntimeError('sin hueco para un dibujo')
        y += (k-p)//2; x += (k-p)//2; spots.append((x, y, p))
        m[max(0, y-GAP):y+p+GAP, max(0, x-GAP):x+p+GAP] = True
    cost = np.zeros((NPAL, NPAL))
    for i, (w, r, cc, d) in enumerate(words):
        n = len(w); wx, wy = cxy(r + (n-1)/2*(d == 'D'), cc + (n-1)/2*(d == 'A'))
        for j, (x, y, p) in enumerate(spots):
            cost[i, j] = np.hypot(x+p/2-wx-s/2, y+p/2-wy-s/2)
    _, cj = linear_sum_assignment(cost)

    L, LET, CELLS = [], {}, set()
    for i, (w, r, cc, d) in enumerate(words):
        num = i+1; dr, dc = (0, 1) if d == 'A' else (1, 0)
        for k, ch in enumerate(w):
            x, y = cxy(r+dr*k, cc+dc*k); CELLS.add((r+dr*k, cc+dc*k))
            LET[(r+dr*k, cc+dc*k)] = f'\\letra{{{x+s/2:.2f}}}{{{RH-y-s/2:.2f}}}{{{ch}}}'
        if d == 'A':
            x, y = cxy(r, cc-1); L.append(f'\\numhor{{{x+s-1.2:.2f}}}{{{RH-y-s/2:.2f}}}{{{num}}}')
        else:
            x, y = cxy(r-1, cc); L.append(f'\\numver{{{x+s/2:.2f}}}{{{RH-y-s+1.2:.2f}}}{{{num}}}')
        x, y, p = spots[cj[i]]; name = nombre(w); a = ASP.get(name, 1.0)
        NH = 5.0; NW = 3.2*len(str(num)) + 1.0          # franja del número: arriba o a la izquierda
        wa = min(p, (p-NH)*a); ha = wa/a; hb = min(p, (p-NW)/a); wb = hb*a
        if wa*ha >= wb*hb:
            wi, hi = wa, ha; xi = x + (p-wi)/2; yi = y + p - hi; nx, ny = xi, yi - NH
        else:
            wi, hi = wb, hb; xi = x + (p - wi - NW)/2 + NW; yi = y + (p-hi)/2; nx, ny = xi - NW, yi
        L.append(f'\\pic{{{xi:.2f}}}{{{RH-yi-hi:.2f}}}{{{wi:.2f}}}{{{hi:.2f}}}{{{name}}}')
        L.append(f'\\numpic{{{nx:.2f}}}{{{RH-ny:.2f}}}{{{num}}}')
    # aristas únicas, fusionadas en tramos
    Hs, Vs = set(), set()
    for (r, cc) in CELLS:
        Hs |= {(r, cc), (r+1, cc)}; Vs |= {(cc, r), (cc+1, r)}
    def runs(keys):
        out = []
        for a in sorted({k[0] for k in keys}):
            bs = sorted(k[1] for k in keys if k[0] == a); st = pv = bs[0]
            for b in bs[1:] + [None]:
                if b is not None and b == pv+1: pv = b; continue
                out.append((a, st, pv-st+1))
                if b is not None: st = pv = b
        return out
    E = 0.16; lines = []
    for rr, c_, n in runs(Hs):
        x, y = cxy(rr, c_); lines.append(f'\\put({x-E:.2f},{RH-y:.2f}){{\\line(1,0){{{n*s+2*E:.2f}}}}}')
    for c_, r_, n in runs(Vs):
        x, y = cxy(r_, c_); lines.append(f'\\put({x:.2f},{RH-y-n*s-E:.2f}){{\\line(0,1){{{n*s+2*E:.2f}}}}}')
    return {'s': s, 'cuerpo': lines + L, 'letras': list(LET.values()),
            'numeracion': [(i+1, w, 'horizontal' if d == 'A' else 'vertical') for i, (w, r, cc, d) in enumerate(words)],
            'celdas': {f'{r},{cc}': ch for (r, cc), ch in
                       [((r+(d == 'D')*k, cc+(d == 'A')*k), ch) for w, r, cc, d in words for k, ch in enumerate(w)]}}


def generar_una(sel, semilla, procesos, rondas, objetivo=14.0):
    cands = []; best = (0, None, None)
    for ronda in range(rondas):
        tareas = [(sel, semilla + ronda*procesos + j, 1500) for j in range(procesos)]
        with MPool(procesos) as mp:
            cands += [c for r in mp.map(trabajo, tareas) for c in r]
        best = mejor(cands)
        if best[0] >= objetivo: break
    return best, len(cands)


def filtrar_leccion(palabras, leccion):
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, raiz)
    import validador_grafemas as v
    tabla = v.cargar_tabla(os.path.join(raiz, 'TABLA_PROGRESION.md'))
    return {w: i for w, i in palabras.items() if v.leccion_minima(w, tabla)[0] <= leccion}


def main():
    global ASP
    ap = argparse.ArgumentParser()
    ap.add_argument('carpeta'); ap.add_argument('--n', type=int, default=25)
    ap.add_argument('--semilla', type=int, default=2026); ap.add_argument('--leccion', type=int)
    ap.add_argument('--max-usos', type=int, default=4); ap.add_argument('--fijas')
    ap.add_argument('--extra'); ap.add_argument('--procesos', type=int, default=os.cpu_count() or 4)
    a = ap.parse_args()
    ASP = json.load(open(os.path.join(a.carpeta, 'aspectos.json')))
    palabras = dict(PALABRAS)
    if a.extra: palabras.update(cargar_extra(a.extra))
    if a.leccion: palabras = filtrar_leccion(palabras, a.leccion)
    faltan = [w for w in palabras if nombre(w) not in ASP]
    if faltan: sys.exit(f'Sin pictograma preparado (ejecuta pictos.py): {faltan}')
    fijas = json.load(open(a.fijas)) if a.fijas else None
    n = len(fijas) if fijas else a.n
    print(f'{len(palabras)} palabras disponibles · {n} cruzadas · máximo {a.max_usos} usos')
    if len(palabras) < NPAL: sys.exit('No hay palabras suficientes para una cruzada.')
    rng = random.Random(a.semilla); uso = {w: 0 for w in palabras}
    for k in range(1, n+1):
        semilla = a.semilla*10000 + k*100
        if fijas:
            sel = fijas[k-1]
            fuera = [w for w in sel if w not in palabras]
            if len(sel) != NPAL or fuera: sys.exit(f'cr-{k:02d}: lista fija incorrecta {fuera}')
            choques = [w for w in sel if en_conflicto(w, set(sel) - {w})]
            if choques: print(f'cr-{k:02d}: AVISO, palabras que se confunden entre sí: {choques}')
            (s, c, res), nc = generar_una(sel, semilla, a.procesos, 4)
        else:
            disp = [w for w in palabras if uso[w] < a.max_usos]
            sub = sorted(disp, key=lambda w: (uso[w], rng.random()))[:30]
            (s, c, res), nc = generar_una(sub, semilla, a.procesos, 3)
            if s < 13.0:                       # cambiar las dos más largas por cortas poco usadas
                sel = [w for _, w, _ in res['numeracion']]
                largas = sorted(sel, key=len, reverse=True)[:2]; base = [w for w in sel if w not in largas]
                cortas = [w for w in sorted(disp, key=lambda w: (uso[w], len(w), rng.random()))
                          if len(w) <= 5 and w not in sel]
                nuevas = []
                for w in cortas:
                    if not en_conflicto(w, base + nuevas): nuevas.append(w)
                    if len(nuevas) == 2: break
                (s2, c2, res2), nc2 = generar_una(base + nuevas, semilla + 50, a.procesos, 3)
                if s2 > s: s, c, res, nc = s2, c2, res2, nc + nc2
        if res is None: sys.exit(f'cr-{k:02d}: no se encontró ninguna rejilla válida.')
        for _, w, _ in res['numeracion']: uso[w] += 1
        json.dump(res, open(os.path.join(a.carpeta, f'cr_{k:02d}.json'), 'w'), ensure_ascii=False)
        print(f'cr-{k:02d}: casilla {s} mm ({nc} rejillas):',
              ' '.join(w for _, w, _ in res['numeracion']), flush=True)
    usados = {w: u for w, u in uso.items() if u}
    print(f'Palabras distintas: {len(usados)} · uso máximo: {max(usados.values())}')


if __name__ == '__main__':
    main()
