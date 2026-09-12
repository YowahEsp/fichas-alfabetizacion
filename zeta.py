#!/usr/bin/env python3
"""Sustituye el glifo 'z' de la familia Memima por una z ligada moderna.

La z original usa el trazo caligráfico antiguo con bucle descendente, que se
confunde con un 3. Esta versión dibuja la z de imprenta ligada: horizontal
superior, diagonal y horizontal inferior, con entrada y salida de ligado.

El trazo es monolínea (grosor constante), igual que el resto de la fuente.
Se construye como centerline engrosada y se une con skia-pathops.
"""
import math, sys
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.reverseContourPen import ReverseContourPen
import pathops

GROSOR = 10.0        # radio del trazo (la fuente va de -10 a 0 en la base)
ALTURAX = 250.0      # altura x medida en a, o, n, e
AVANCE = 400
LIGADO = 108.0     # altura a la que ligan todas las letras (medida en a,e,o,u,n,x)

def bezier3(p0, p1, p2, p3, n=18):
    pts = []
    for i in range(n + 1):
        t = i / n; u = 1 - t
        pts.append((u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
                    u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]))
    return pts

def bezier2(p0, p1, p2, n=14):
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append((u*u*p0[0] + 2*u*t*p1[0] + t*t*p2[0],
                    u*u*p0[1] + 2*u*t*p1[1] + t*t*p2[1]))
    return pts

def centerline():
    pts = []
    # Entrada: arranca con la MISMA inclinación con la que muere el trazo de la
    # vocal (50 grados, medido rasterizando la 'a') y se tumba hasta entrar
    # horizontal en el trazo superior.
    pts += bezier3((0, LIGADO), (35, 153), (68, ALTURAX), (100, ALTURAX))
    # horizontal superior
    pts += [(330, ALTURAX)]
    # diagonal descendente, esquina inferior redondeada
    pts += [(96, 12)]
    pts += bezier2((96, 12), (86, 0), (118, 0), n=8)
    # horizontal inferior
    pts += [(292, 0)]
    # salida: esquina suave y recta ascendente a esos mismos 50 grados
    pts += bezier2((292, 0), (312, 0), (330, 22), n=8)
    pts += [(AVANCE, LIGADO)]
    # quita duplicados consecutivos
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0]-out[-1][0]) > 0.01 or abs(p[1]-out[-1][1]) > 0.01:
            out.append(p)
    return out

def area(pts):
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]; x2, y2 = pts[(i+1) % len(pts)]
        s += x1*y2 - x2*y1
    return s / 2

def horario(pts):
    return pts if area(pts) < 0 else pts[::-1]

def disco(cx, cy, r, n=16):
    return [(cx + r*math.cos(2*math.pi*i/n), cy + r*math.sin(2*math.pi*i/n))
            for i in range(n)]

def barra(p, q, r):
    dx, dy = q[0]-p[0], q[1]-p[1]
    L = math.hypot(dx, dy)
    if L == 0:
        return None
    nx, ny = -dy/L*r, dx/L*r
    return [(p[0]+nx, p[1]+ny), (q[0]+nx, q[1]+ny),
            (q[0]-nx, q[1]-ny), (p[0]-nx, p[1]-ny)]

def muestrear(pts, paso=3.0):
    """Reparte puntos equiespaciados a lo largo de la polilínea."""
    out = [pts[0]]
    resto = 0.0
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i+1]
        dx, dy = q[0]-p[0], q[1]-p[1]
        L = math.hypot(dx, dy)
        if L == 0:
            continue
        d = paso - resto
        while d <= L:
            out.append((p[0] + dx*d/L, p[1] + dy*d/L))
            d += paso
        resto = (L - (d - paso))
    out.append(pts[-1])
    return out

def construir_z():
    # Solo discos a lo largo del trazo: así las esquinas salen redondeadas.
    # Con rectángulos, los ángulos agudos producían un pico (unión en inglete).
    pts = muestrear(centerline(), paso=3.0)
    piezas = [disco(p[0], p[1], GROSOR, n=24) for p in pts]
    # todas las piezas con la misma orientación antes de unir: con orientaciones
    # mezcladas, union interpreta las contrarias como agujeros
    caminos = []
    for pieza in piezas:
        c = horario(pieza)
        p = pathops.Path()
        pen = p.getPen()
        pen.moveTo(c[0])
        for pt in c[1:]:
            pen.lineTo(pt)
        pen.closePath()
        caminos.append(p)
    final = pathops.Path()
    pathops.union(caminos, final.getPen(), clockwise=True)
    return final

def injertar(origen, destino):
    font = TTFont(origen)
    z = construir_z()
    pen = TTGlyphPen(font.getGlyphSet())
    z.draw(pen)
    font['glyf']['z'] = pen.glyph()
    font['hmtx']['z'] = (AVANCE, 0)
    font.save(destino)
    print(f'{destino}: z sustituida, avance {AVANCE}')

if __name__ == '__main__':
    injertar(sys.argv[1], sys.argv[2])
