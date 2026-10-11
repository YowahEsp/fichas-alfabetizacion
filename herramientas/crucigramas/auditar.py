"""Auditoría independiente de un .tex de cruzadas (hecho con montar.py).

Uso:  python3 auditar.py <archivo.tex> [--max-usos 4] [--leccion L] [--extra extra.txt]

No usa los datos internos del generador: reconstruye cada página a partir de las coordenadas
del .tex y comprueba lo que verá el alumno. Termina con código 1 si encuentra errores.

Comprobaciones por cruzada:
  · ficha y solución idénticas (rejilla, números, dibujos); la ficha no muestra letras
  · cada casilla dibujada tiene una letra en la solución y ninguna letra está fuera de casilla
  · las letras forman exactamente 18 palabras, numeradas 1–18 sin números repetidos
  · el número de cada dibujo corresponde al dibujo de su palabra
  · ningún cruce en letra con tilde; ningún hueco vacío encerrado por casillas
  · ninguna caja (casilla, número o dibujo) se solapa con otra ni sale de la zona 281 × 177 mm
Comprobaciones del repertorio:
  · palabras de la lista cerrada (más --extra), usos ≤ --max-usos, sin pares en conflicto
  · con --leccion, todas las palabras admitidas en esa lección (validador del repositorio)
  · si existe el .log junto al .tex, compilación sin errores ni Overfull/Underfull
Después hay que revisar el PDF a la vista, página a página (esto no lo sustituye).
"""
import argparse, os, re, sys
from collections import Counter, defaultdict
from lista import PALABRAS, nombre, en_conflicto, cargar_extra

N = r'(-?[\d.]+)'
RW, RH = 281, 177
ACC = set('áéíóú')


def leer(pg):
    f = lambda pat: [tuple(m) for m in re.findall(pat, pg)]
    return {
        'hl': [tuple(map(float, t)) for t in f(rf'\\put\({N},{N}\)\{{\\line\(1,0\)\{{{N}\}}\}}')],
        'vl': [tuple(map(float, t)) for t in f(rf'\\put\({N},{N}\)\{{\\line\(0,1\)\{{{N}\}}\}}')],
        'nh': [(float(x), float(y), int(n)) for x, y, n in f(rf'\\numhor\{{{N}\}}\{{{N}\}}\{{(\d+)\}}')],
        'nv': [(float(x), float(y), int(n)) for x, y, n in f(rf'\\numver\{{{N}\}}\{{{N}\}}\{{(\d+)\}}')],
        'pic': [(float(x), float(y), float(w), float(h), p) for x, y, w, h, p in
                f(rf'\\pic\{{{N}\}}\{{{N}\}}\{{{N}\}}\{{{N}\}}\{{([^}}]+)\}}')],
        'np': [(float(x), float(y), int(n)) for x, y, n in f(rf'\\numpic\{{{N}\}}\{{{N}\}}\{{(\d+)\}}')],
        'let': [(float(x), float(y), c) for x, y, c in f(rf'\\letra\{{{N}\}}\{{{N}\}}\{{([^}}]+)\}}')],
        'sol': r'\textbf{(Solución)}' in pg,
        'cod': (re.findall(r'\\codigo\{([^}]*)\}', pg) or [None])[0],
    }


def cruzada(A, B, err):
    for k in ('hl', 'vl', 'nh', 'nv', 'pic', 'np'):
        if sorted(A[k]) != sorted(B[k]): err(f'{k}: distinto entre ficha y solución')
    if A['let']: err('la ficha muestra letras')
    if A['sol'] or not B['sol']: err('marca «(Solución)» mal puesta')
    if A['cod'] != B['cod']: err('código distinto en ficha y solución')
    dup = sum(c - 1 for c in Counter(A['hl'] + A['vl']).values() if c > 1)
    if dup: err(f'{dup} líneas duplicadas')
    L = B['let']
    if not L: err('la solución no tiene letras'); return [], None
    xs = sorted({round(x, 2) for x, _, _ in L}); ys = sorted({round(y, 2) for _, y, _ in L})
    S = min([b - a for a, b in zip(xs, xs[1:]) if b - a > 1] + [b - a for a, b in zip(ys, ys[1:]) if b - a > 1])
    S = round(S * 4) / 4
    x0, y1 = min(xs), max(ys)
    G = {}
    for x, y, c in L:
        fr, fc = (y1 - y) / S, (x - x0) / S
        if abs(fr - round(fr)) > .02 or abs(fc - round(fc)) > .02: err(f'letra «{c}» fuera de la cuadrícula')
        p = (round(fr), round(fc))
        if p in G: err(f'dos letras en la misma casilla {p}')
        G[p] = c
    # casillas dibujadas, a partir de las aristas
    H, V = set(), set()
    for x, y, l in A['hl']:
        r = round((y1 + S/2 - y) / S); c0 = round((x + .16 - (x0 - S/2)) / S)
        for i in range(round((l - .32) / S)): H.add((r, c0 + i))
    for x, y, l in A['vl']:
        c = round((x - (x0 - S/2)) / S); r0 = round((y1 + S/2 - (y + l - .16)) / S)
        for i in range(round((l - .32) / S)): V.add((r0 + i, c))
    dibujadas = {(r, c) for r, c in H if (r + 1, c) in H and (r, c) in V and (r, c + 1) in V}
    if dibujadas - set(G): err(f'{len(dibujadas - set(G))} casillas sin letra')
    if set(G) - dibujadas: err(f'{len(set(G) - dibujadas)} letras sin casilla')
    # palabras
    pal = {}
    for (r, c), ch in G.items():
        if (r, c - 1) not in G and (r, c + 1) in G:
            w = ''; j = c
            while (r, j) in G: w += G[(r, j)]; j += 1
            pal[('H', r, c)] = w
        if (r - 1, c) not in G and (r + 1, c) in G:
            w = ''; j = r
            while (j, c) in G: w += G[(j, c)]; j += 1
            pal[('V', r, c)] = w
    if len(pal) != 18: err(f'{len(pal)} palabras en la rejilla (deben ser 18)')
    # números de palabra
    num = {}
    for x, y, n in A['nh']:
        p = ('H', round((y1 - y) / S), round((x + 1.2 + S/2 - x0) / S))
        if p not in pal: err(f'nº {n} (horizontal) no está delante de ninguna palabra')
        elif n in num: err(f'nº {n} repetido')
        else: num[n] = pal[p]
    for x, y, n in A['nv']:
        p = ('V', round((y1 - (y - 1.2 - S/2)) / S), round((x - x0) / S))
        if p not in pal: err(f'nº {n} (vertical) no está encima de ninguna palabra')
        elif n in num: err(f'nº {n} repetido')
        else: num[n] = pal[p]
    if sorted(num) != list(range(1, 19)): err(f'números de palabra incompletos: {sorted(num)}')
    if len(set(num.values())) != len(num): err('palabra repetida en la cruzada')
    # números de dibujo -> dibujo -> palabra
    for x, y, n in A['np']:
        def d(p):
            px, py, pw, ph, _ = p; top = py + ph
            return min(abs(px - x) + abs(top + 5 - y), abs(top - y) + (0 if 3 <= px - x <= 9 else 99))
        p = min(A['pic'], key=d)
        if d(p) > 0.5: err(f'nº de dibujo {n} sin dibujo junto a él')
        elif n in num and nombre(num[n]) != p[4]:
            err(f'nº {n}: dibujo «{p[4]}» pero la palabra es «{num[n]}»')
    # cruces con tilde
    for (r, c), ch in G.items():
        if ch in ACC and ((r, c - 1) in G or (r, c + 1) in G) and ((r - 1, c) in G or (r + 1, c) in G):
            err(f'cruce en letra con tilde «{ch}»')
    # huecos encerrados
    R0, R1 = min(r for r, _ in G) - 1, max(r for r, _ in G) + 1
    C0, C1 = min(c for _, c in G) - 1, max(c for _, c in G) + 1
    vistos, pila = set(), [(R0, C0)]
    while pila:
        p = pila.pop()
        if p in vistos or p in G or not (R0 <= p[0] <= R1 and C0 <= p[1] <= C1): continue
        vistos.add(p); pila += [(p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)]
    cerr = (R1 - R0 + 1) * (C1 - C0 + 1) - len(G) - len(vistos)
    if cerr: err(f'{cerr} posiciones vacías encerradas por casillas')
    # solapes
    cajas = [('casilla', (x0 + c*S - S/2, y1 - r*S - S/2, x0 + c*S + S/2, y1 - r*S + S/2)) for r, c in G]
    for x, y, n in A['nh']: w = 3.2 * len(str(n)); cajas.append((f'nº {n}', (x - w, y - 2, x, y + 2)))
    for x, y, n in A['nv']: w = 3.2 * len(str(n)); cajas.append((f'nº {n}', (x - w/2, y, x + w/2, y + 4)))
    for x, y, n in A['np']: w = 3.4 * len(str(n)); cajas.append((f'nº dibujo {n}', (x, y - 4.2, x + w, y)))
    for x, y, w, h, p in A['pic']: cajas.append((f'dibujo {p}', (x, y, x + w, y + h)))
    def corta(a, b, m=0.2): return a[0] < b[2] - m and b[0] < a[2] - m and a[1] < b[3] - m and b[1] < a[3] - m
    for i, (na, a) in enumerate(cajas):
        if a[0] < -.01 or a[1] < -.01 or a[2] > RW + .01 or a[3] > RH + .01: err(f'{na} sale de la zona')
        for nb, b in cajas[i + 1:]:
            if not (na == nb == 'casilla') and corta(a, b): err(f'solape: {na} / {nb}')
    menor = min((max(w, h) for *_, w, h, _ in A['pic']), default=0)
    return list(num.values()), (S, menor)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tex'); ap.add_argument('--max-usos', type=int, default=4)
    ap.add_argument('--leccion', type=int); ap.add_argument('--extra')
    a = ap.parse_args()
    src = open(a.tex, encoding='utf-8').read()
    cuerpo = src[src.index(r'\begin{document}'):]
    paginas = re.split(r'\\nuevaficha', cuerpo)
    if len(paginas) % 2: sys.exit(f'Número impar de páginas ({len(paginas)}): faltan fichas o soluciones.')
    n = len(paginas) // 2
    lista = dict(PALABRAS)
    if a.extra: lista.update(cargar_extra(a.extra))
    total = 0; uso = Counter(); filas = []
    for k in range(n):
        A, B = leer(paginas[k]), leer(paginas[k + n]); cod = A['cod'] or f'nº {k + 1}'
        errores = []
        palabras, info = cruzada(A, B, errores.append)
        for w in palabras:
            if w not in lista: errores.append(f'«{w}» no está en la lista cerrada')
            if en_conflicto(w, set(palabras) - {w}): errores.append(f'«{w}» en conflicto con otra palabra')
        uso.update(palabras); total += len(errores)
        filas.append((cod, info, palabras))
        estado = 'OK' if not errores else f'{len(errores)} ERRORES'
        print(f'{cod}: casilla {info[0] if info else "?"} mm · {estado}')
        for e in errores[:15]: print('    ', e)
    exceso = {w: u for w, u in uso.items() if u > a.max_usos}
    if exceso: total += len(exceso); print('Palabras por encima de', a.max_usos, 'usos:', exceso)
    if a.leccion:
        raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.insert(0, raiz); import validador_grafemas as v
        tabla = v.cargar_tabla(os.path.join(raiz, 'TABLA_PROGRESION.md'))
        malas = {w: v.leccion_minima(w, tabla)[0] for w in uso if v.leccion_minima(w, tabla)[0] > a.leccion}
        if malas: total += len(malas); print(f'Palabras que no admite L{a.leccion}:', malas)
    log = os.path.splitext(a.tex)[0] + '.log'
    if os.path.exists(log):
        av = re.findall(r'^(!.*|Overfull.*|Underfull.*)$', open(log, errors='replace').read(), re.M)
        if av: total += len(av); print('Compilación:', av[:5])
    tam = [f[1][0] for f in filas if f[1]]
    print(f'\n{n} cruzadas · {len(uso)} palabras distintas · uso máximo {max(uso.values())} · '
          f'casilla {min(tam)}–{max(tam)} mm ({sum(t >= 14 for t in tam)} de {n} ≥ 14 mm)')
    print('RESULTADO:', 'SIN ERRORES' if total == 0 else f'{total} ERRORES')
    sys.exit(1 if total else 0)


if __name__ == '__main__':
    main()
