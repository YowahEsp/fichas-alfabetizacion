"""Monta el .tex de las cruzadas: todas las fichas y, detrás, todas las soluciones.

Uso:  python3 montar.py <carpeta> [--salida CRUCIGRAMAS_cr-01-cr-25] [--prefijo cr]
                        [--sin-codigo] [--compilar]

Lee <carpeta>/cr_XX.json (de generar.py) y copia PLANTILLA_MAESTRA.tex del repositorio,
sustituyendo solo la sección de ejemplo. Folio A4 apaisado con \\geometry en la sección de
entrega; rejilla con el entorno picture de LaTeX (la plantilla no carga TikZ y su preámbulo
no se toca). El código (cr-01…) va pequeño y gris abajo a la derecha, para la docente.
Con --compilar ejecuta XeLaTeX en la carpeta (necesita allí MemimaM.ttf, Mestra1M.ttf,
Mestra2M.ttf y la carpeta pictos/).
"""
import argparse, glob, json, os, re, subprocess, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CABECERA = r'''% ============================================================================
%  ENTREGA — Cruzadas con pictogramas (@PRIMERO@ a @ULTIMO@)
%  Páginas 1–@N@: cruzadas. Páginas @N1@–@N2@: soluciones, en el mismo orden.
%  Generado con herramientas/crucigramas (formato aprobado en CRUCIGRAMA_L45_01).
% ============================================================================
\geometry{landscape,left=8mm,right=8mm,top=7mm,bottom=5mm}   % folio apaisado
% Aristas: cada una se dibuja una sola vez (\line), en tramos fusionados.
% Números de palabra fuera de la rejilla: a la izquierda (horizontal) o encima (vertical).
\newcommand{\numhor}[3]{\put(#1,#2){\makebox(0,0)[r]{\bfseries\fontsize{15pt}{15pt}\selectfont #3}}}
\newcommand{\numver}[3]{\put(#1,#2){\makebox(0,0)[b]{\bfseries\fontsize{15pt}{15pt}\selectfont #3}}}
% \pic{x}{y}{ancho}{alto}{pictograma}  ·  \numpic{x}{y}{número}   (mm, origen abajo a la izquierda)
\newcommand{\pic}[5]{\put(#1,#2){\makebox(0,0)[lb]{\includegraphics[width=#3mm,height=#4mm]{pictos/#5}}}}
\newcommand{\numpic}[3]{\put(#1,#2){\makebox(0,0)[lt]{\bfseries\fontsize{16pt}{16pt}\selectfont #3}}}
% \letra{x}{y}{letra}: solución en MemimaM, centrada en su casilla, línea base común.
% Cuerpo proporcional a la casilla (36 pt para 14,75 mm): de la cola de la q al asta de la l
% miden 1,018 em, así que caben todas con margen.
\newcommand{\tamletra}{36pt}
\newcommand{\letra}[3]{\put(#1,#2){\makebox(0,0){\ligada\fontsize{\tamletra}{\tamletra}\selectfont
  \smash{\raisebox{-0.126em}{#3}}}}}
\newcommand{\codigo}[1]{\hfill{\footnotesize\color{gray}#1}}

\begin{document}
'''


def pagina(d, codigo, sol, primera):
    t = [] if primera else [r'\nuevaficha']
    t.append(f'% ---------- {codigo}{" · SOLUCIÓN" if sol else ""} · casilla {d["s"]} mm ----------')
    t.append(r'\enunciado{accion_escribir}{Escribe en el crucigrama el nombre de cada dibujo.'
             + (r' \textbf{(Solución)}' if sol else '') + '}')
    if sol: t.append(r'\renewcommand{\tamletra}{%.1fpt}' % (36 * d['s'] / 14.75))
    t += [r'\vspace*{-1mm}', r'\noindent{\setlength{\unitlength}{1mm}\linethickness{0.9pt}%',
          r'\begin{picture}(281,177)']
    t += d['cuerpo']
    if sol: t += d['letras']
    t += [r'\end{picture}}', r'\atribucion' + (r'\codigo{%s}' % codigo if codigo else '')]
    return '\n'.join(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('carpeta'); ap.add_argument('--salida'); ap.add_argument('--prefijo', default='cr')
    ap.add_argument('--sin-codigo', action='store_true'); ap.add_argument('--compilar', action='store_true')
    a = ap.parse_args()
    archivos = sorted(glob.glob(os.path.join(a.carpeta, 'cr_*.json')))
    if not archivos: sys.exit('No hay cr_XX.json en la carpeta (ejecuta generar.py).')
    datos = [json.load(open(f)) for f in archivos]; n = len(datos)
    cod = [f'{a.prefijo}-{k:02d}' for k in range(1, n+1)]
    salida = a.salida or f'CRUCIGRAMAS_{cod[0]}-{cod[-1]}'
    tpl = open(os.path.join(RAIZ, 'PLANTILLA_MAESTRA.tex'), encoding='utf-8').read()
    corte = tpl.rindex('% ====', 0, tpl.index('%  EJEMPLO DE USO'))
    cab = (CABECERA.replace('@PRIMERO@', cod[0]).replace('@ULTIMO@', cod[-1])
           .replace('@N1@', str(n+1)).replace('@N2@', str(2*n)).replace('@N@', str(n)))
    paginas = [pagina(d, None if a.sin_codigo else c, False, k == 0) for k, (d, c) in enumerate(zip(datos, cod))]
    paginas += [pagina(d, None if a.sin_codigo else c, True, False) for d, c in zip(datos, cod)]
    tex = os.path.join(a.carpeta, salida + '.tex')
    open(tex, 'w', encoding='utf-8').write(tpl[:corte] + cab + '\n\n'.join(paginas) + '\n\n\\end{document}\n')
    print(f'{tex}: {n} cruzadas + {n} soluciones')
    if a.compilar:
        subprocess.run(['xelatex', '-interaction=nonstopmode', salida + '.tex'], cwd=a.carpeta,
                       stdout=subprocess.DEVNULL)
        log = open(os.path.join(a.carpeta, salida + '.log'), encoding='utf-8', errors='replace').read()
        avisos = re.findall(r'^(!.*|Overfull.*|Underfull.*)$', log, re.M)
        print('Compilación:', 'sin errores ni avisos' if not avisos else avisos[:10])


if __name__ == '__main__':
    main()
