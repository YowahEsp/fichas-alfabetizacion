# Cruzadas con pictogramas

Herramientas para generar cruzadas (crucigramas) con pictogramas de ARASAAC según el formato aprobado en `CRUCIGRAMA_L45_01` y en el repertorio `cr-01…cr-25`: A4 apaisado, 18 palabras, casillas lo más grandes posible, dibujos repartidos junto a sus palabras y soluciones en letra ligada.

| Archivo | Función |
|---|---|
| `lista.py` | Lista cerrada de 149 palabras con el pictograma de ARASAAC revisado a mano, pares que no pueden ir juntos y retoques (policía). |
| `pictos.py` | Descarga los pictogramas en blanco y negro, recorta el margen y los aplana sobre blanco. |
| `generar.py` | Crea las rejillas y coloca los dibujos (`cr_XX.json`). |
| `montar.py` | Escribe el `.tex` sobre `PLANTILLA_MAESTRA.tex`: todas las fichas y detrás todas las soluciones. Opcionalmente compila. |
| `auditar.py` | Auditoría independiente del `.tex` terminado. |

Necesita Python 3 con `numpy`, `scipy` y `Pillow`, `curl` y XeLaTeX. Las fuentes Memima **no** están aquí: se reconstruyen desde `FUENTES_MEMIMA_BASE64.txt` del Proyecto, como siempre.

## Uso

```bash
cd herramientas/crucigramas
T=/home/claude/trabajo_cruzadas                     # carpeta de trabajo (fuera del repositorio)
python3 pictos.py $T                                # 1. pictogramas (una vez; luego reutiliza)
python3 generar.py $T --n 25 --semilla 2026         # 2. rejillas (≈ 1 h para 25)
cp ../../MemimaM.ttf ../../Mestra1M.ttf ../../Mestra2M.ttf $T/
python3 montar.py $T --compilar                     # 3. .tex y PDF
python3 auditar.py $T/CRUCIGRAMAS_cr-01-cr-25.tex   # 4. auditoría: debe decir SIN ERRORES
```

Después, **revisar el PDF a la vista**, cada cruzada junto a su solución y a 300 ppp las zonas dudosas. La auditoría no sustituye esa revisión.

### Opciones de `generar.py`

- `--leccion L`: solo palabras admitidas en esa lección de Palau, con el validador del repositorio. Con L45 quedan 81 palabras. En lecciones bajas puede no haber suficientes.
- `--max-usos 4`: veces que puede salir cada palabra en todo el repertorio.
- `--fijas fijas.json`: lista de listas de 18 palabras, una por cruzada; se respetan tal cual. Avisa si hay palabras que se confunden entre sí.
- `--extra extra.txt`: palabras añadidas, una por línea (`palabra id_arasaac`). Su pictograma hay que revisarlo antes, con los mismos criterios que los de `lista.py`. También hay que pasar `--extra` a `pictos.py` y a `auditar.py`.
- `--semilla`: otra semilla da otro repertorio.

### Opciones de `montar.py`

- `--salida NOMBRE`: nombre del `.tex`/PDF (por defecto `CRUCIGRAMAS_cr-01-cr-NN`).
- `--prefijo cr`: prefijo del código de cada ficha.
- `--sin-codigo`: no pone el código en la esquina.

## Reglas que aplica (no cambiarlas sin hablarlo con la docente)

- Casilla máxima, con un objetivo de 14 mm o más; si no se llega a 13 mm, se cambian las dos palabras más largas por otras cortas (salvo con `--fijas`).
- Números de palabra **fuera** de la rejilla: a la izquierda en las horizontales y encima en las verticales. Así nunca se superponen.
- Ningún cruce en letra con tilde. La ñ solo cruza con ñ. Ningún hueco vacío encerrado por casillas, porque parecería una casilla más.
- Dibujos en huecos de 24 a 32 mm con 2 mm de aire, junto a su palabra y con el número dentro de su hueco.
- Solución en MemimaM negra, con un cuerpo proporcional a la casilla y «(Solución)» en el enunciado.

## Lo que salió mal antes (para no repetirlo)

- Los números dentro de la casilla se superponían.
- Las casillas «fantasma» las dejaban los huecos cerrados.
- Los dibujos se ponían en bloque aparte o apilados cada 14 mm (miden 24).
- Había palabras sin tilde.
- Se usaron pictogramas de otra palabra, con texto o con flechas.
- Los informes de un generador externo daban por buenas cosas falsas. Por eso todo `.tex` se audita con `auditar.py`, venga de donde venga.
