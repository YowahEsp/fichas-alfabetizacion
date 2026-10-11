"""Descarga y prepara los pictogramas de ARASAAC de la lista cerrada.

Uso:  python3 pictos.py <carpeta_de_trabajo> [--extra extra.txt]

Crea <carpeta>/pictos/<nombre>.png (blanco y negro, margen recortado, aplanado sobre blanco
puro: los semitransparentes dejaban un rectángulo gris al imprimir) y <carpeta>/aspectos.json
(proporción ancho/alto de cada dibujo, que usa el generador). Lo ya descargado no se repite.
"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image
from lista import PALABRAS, RETOQUES, PICTO_ENUNCIADO, nombre, cargar_extra

URL = 'https://api.arasaac.org/v1/pictograms/{}?color=false&resolution=500'


def descargar(ident, destino):
    for intento in range(4):
        if os.path.exists(destino) and os.path.getsize(destino) > 1000:
            return True
        subprocess.run(['curl', '-sS', '-m', '45', '-o', destino, URL.format(ident)])
        time.sleep(1)
    return os.path.exists(destino) and os.path.getsize(destino) > 1000


def preparar(origen, destino, retoque=None):
    im = Image.open(origen).convert('RGBA')
    if retoque:
        (x0, y0, x1, y1), sin_suelo = retoque
        a = np.array(im)
        if sin_suelo:                                   # filas casi llenas = línea del suelo
            lleno = (a[:, :, 3] > 20).sum(1) > 0.6 * a.shape[1]
            a[lleno, :, 3] = 0
        im = Image.fromarray(a).crop((x0, y0, x1, y1))
    caja = im.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox()
    im = im.crop(caja); w, h = im.size; m = int(0.02 * max(w, h))
    lienzo = Image.new('RGBA', (w + 2*m, h + 2*m), (255, 255, 255, 255))
    lienzo.alpha_composite(im, (m, m))
    g = np.array(lienzo.convert('L')); g[g > 225] = 255
    Image.fromarray(g).save(destino)
    return lienzo.size[0] / lienzo.size[1]


if __name__ == '__main__':
    base = sys.argv[1]
    palabras = dict(PALABRAS)
    if '--extra' in sys.argv: palabras.update(cargar_extra(sys.argv[sys.argv.index('--extra') + 1]))
    crudo = os.path.join(base, 'pictos_arasaac'); final = os.path.join(base, 'pictos')
    os.makedirs(crudo, exist_ok=True); os.makedirs(final, exist_ok=True)
    tareas = [(w, i) for w, i in palabras.items()] + [('accion_escribir', PICTO_ENUNCIADO)]
    with ThreadPoolExecutor(4) as ex:
        ok = list(ex.map(lambda t: descargar(t[1], os.path.join(crudo, f'{t[1]}.png')), tareas))
    faltan = [t for t, o in zip(tareas, ok) if not o]
    if faltan:
        sys.exit(f'No se pudieron descargar: {faltan}. Vuelve a ejecutar el script.')
    aspectos = {}
    for w, i in tareas:
        aspectos[nombre(w)] = preparar(os.path.join(crudo, f'{i}.png'),
                                       os.path.join(final, f'{nombre(w)}.png'), RETOQUES.get(w))
    json.dump(aspectos, open(os.path.join(base, 'aspectos.json'), 'w'), indent=0)
    print(f'{len(aspectos)} pictogramas listos en {final}')
