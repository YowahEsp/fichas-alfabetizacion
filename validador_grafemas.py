#!/usr/bin/env python3
"""
validador_grafemas.py — Proyecto «Fichas de alfabetización» (EPA, método Palau)

Comprueba que un texto solo contiene grafemas, estructuras silábicas y signos
ya introducidos en una lección dada. La fuente de verdad es TABLA_PROGRESION.md:
el validador la lee y no lleva la secuencia escrita dentro. Si la tabla cambia,
el validador cambia con ella; si la tabla contiene algo que no entiende, se
detiene en lugar de suponer.

Uso:
    python3 validador_grafemas.py -l 9 casa perro rueda
    python3 validador_grafemas.py -l 9 -f vocabulario.txt
    python3 validador_grafemas.py -l 40 --imprenta -f frases.txt
    python3 validador_grafemas.py -l 9 --explicar rueda
    python3 validador_grafemas.py -l 4 --tex FICHA_LE_m_01.tex
    python3 validador_grafemas.py --inventario 9

Código de salida: 0 si todo se admite, 1 si hay rechazos, 2 si hay error de uso
o de lectura de la tabla.

Reglas fijas (decisiones de la docente, ver §5 de la tabla):
  D2  diptongos, triptongos e hiatos: válidos desde L1 (son vocales seguidas).
  D3  la tilde no es grafema nuevo.
  D4  ligada: la mayúscula va con su minúscula. Imprenta: opción --imprenta.
"""
import argparse, os, re, sys, unicodedata, urllib.request

URL_TABLA = ("https://raw.githubusercontent.com/YowahEsp/"
             "fichas-alfabetizacion/main/TABLA_PROGRESION.md")

VOCALES = set("aeiouáéíóúü")
ACENTOS = str.maketrans("áéíóúü", "aeiouu")
LETRAS = r"a-zA-ZáéíóúüñÁÉÍÓÚÜÑ"

# Vocabulario de la columna «Grafemas nuevos» → clave interna
TOKENS = {
    "a": "V", "e": "V", "i": "V", "o": "V", "u": "V",
    "m": "m", "t": "t", "n": "n", "p": "p", "l": "l", "d": "d", "s": "s",
    "r-fuerte": "R_F", "rr": "rr", "v": "v", "h": "h", "b": "b", "ll": "ll",
    "y-cons": "Y_CONS", "y-voc": "Y_VOC", "y-nexo": "Y_NEXO", "ch": "ch",
    "f": "f", "z": "z", "c(e,i)": "C_EI", "j": "j", "g(e,i)": "G_EI",
    "g(a,o,u)": "g", "gu(e,i)": "gu", "c(a,o,u)": "C_K", "qu": "qu",
    "x": "x", "ñ": "ñ", "r-suave": "R_S",
}
NOMBRE = {  # para los mensajes
    "V": "vocal", "R_F": "r fuerte", "rr": "rr", "R_S": "r suave",
    "Y_CONS": "y consonante", "Y_VOC": "y final", "Y_NEXO": "y (nexo)",
    "C_EI": "c ante e/i", "C_K": "c ante a/o/u", "G_EI": "g ante e/i",
    "g": "g ante a/o/u", "gu": "gu ante e/i", "qu": "qu", "gü": "gü",
}
GRUPOS = {"tr", "dr", "br", "bl", "gr", "gl", "fr", "fl", "pr", "pl", "cr", "cl"}
SIN_LECCION = 10**6   # marcador interno; se sustituye por la lección de apertura


class ErrorTabla(Exception):
    pass


# ----------------------------------------------------------------------------
# Lectura de la tabla
# ----------------------------------------------------------------------------
def _filas(texto, titulo_desde, titulo_hasta=None):
    """Filas de tabla markdown entre dos encabezados."""
    i = texto.find(titulo_desde)
    if i < 0:
        raise ErrorTabla(f"No encuentro la sección «{titulo_desde}» en la tabla.")
    j = texto.find(titulo_hasta, i + 1) if titulo_hasta else -1
    bloque = texto[i:j if j > 0 else None]
    filas = []
    for linea in bloque.splitlines():
        if linea.startswith("|") and not re.match(r"^\|[\s\-|]+\|$", linea):
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            if celdas and re.match(r"^\d", celdas[0]):
                filas.append(celdas)
    return filas


def _limpia(celda):
    return re.sub(r"\*\*|\*", "", celda).strip()


class Tabla:
    def __init__(self, texto):
        self.grafema = {}      # clave → lección (ligada)
        self.imprenta = {}     # clave → lección de imprenta
        self.coda = {}         # consonante → lección
        self.grupo = {}        # 'tr' → lección
        self.especial = {}     # 'es','un','el' → lección
        self.excepcion = {}    # palabra (minúsculas) → lección
        self.signo = {}        # carácter → lección
        self.apertura = None   # D6
        self._leer(texto)

    def _leer(self, t):
        # §2 y §3: grafemas, especiales, bloques de imprenta
        filas = (_filas(t, "## 2. Primera cartilla", "## 3.") +
                 _filas(t, "## 3. Segunda cartilla", "## 4."))
        bloques_imprenta = []
        for c in filas:
            if len(c) < 6:
                raise ErrorTabla(f"Fila con columnas de menos: {c}")
            col_l, col_g, _, col_esp, _, col_obs = c[:6]
            if re.match(r"^\d+\s*[–-]\s*\d+$", col_l):          # bloque de imprenta
                m = re.search(r"imprenta de L(\d+)\s*[–-]\s*L(\d+)", col_g)
                if not m:
                    raise ErrorTabla(f"Bloque de imprenta sin rango: {col_l}")
                bloques_imprenta.append((int(m.group(1)), int(m.group(2)), col_obs))
                continue
            L = int(col_l)
            g = _limpia(col_g)
            if g not in ("—", "-", ""):
                if "¿" in g:
                    continue                                    # signos: ver D4
                for tok in re.split(r",\s*(?![^()]*\))", g):
                    tok = tok.strip()
                    if tok not in TOKENS:
                        raise ErrorTabla(f"L{L}: grafema «{tok}» no reconocido.")
                    clave = TOKENS[tok]
                    if clave != "V":
                        self.grafema[clave] = L
            for esp in re.findall(r"\*\*(\w+)\*\*", col_esp):
                self.especial[esp.lower()] = L
        # imprenta: «13 m, 14 t, …» → lección de ligada correspondiente
        for desde, hasta, obs in bloques_imprenta:
            for num, letras in re.findall(r"(\d+)\s+([a-zñ/]+|vocales)", obs):
                num = int(num)
                if letras == "vocales":
                    self.imprenta["V"] = num
                    continue
                partes = letras.split("/")
                destino = None
                for L in range(desde, hasta + 1):
                    claves = [k for k, v in self.grafema.items() if v == L]
                    bases = {_base(k) for k in claves}
                    if all(p in bases for p in partes):
                        destino = claves
                        break
                if destino is None:
                    raise ErrorTabla(f"Imprenta L{num} «{letras}»: sin lección de origen.")
                for k in destino:
                    self.imprenta[k] = num
        # §4: codas y grupos
        for c in _filas(t, "### 4.1", "### 4.2"):
            letra = _limpia(c[1]).split()[0]
            self.coda[letra] = int(c[0])
        for c in _filas(t, "### 4.2", "### 4.3"):
            nuevas = _limpia(c[3])
            if nuevas not in ("—", "-", ""):
                nuevas = re.sub(r"\(.*?\)", "", nuevas)
                for letra in re.split(r",\s*", nuevas):
                    self.coda[letra.strip()] = int(c[0])
        for c in _filas(t, "### 4.3", "### 4.4"):
            for gr in re.split(r",\s*", _limpia(c[1])):
                self.grupo[gr.strip()] = int(c[0])
        # D6: apertura de la ortografía completa
        m = re.search(r"\[D6\] RESUELTA[^\n]*?Desde \*\*L(\d+)\*\*", t)
        if not m:
            raise ErrorTabla("No encuentro la decisión [D6] resuelta.")
        self.apertura = int(m.group(1))
        # D4: signos
        m = re.search(r"\*\*Signos:\*\*(.+)", t)
        if not m:
            raise ErrorTabla("No encuentro la línea de signos de [D4].")
        for trozo in m.group(1).split(";"):
            n = re.search(r"desde L(\d+)", trozo)
            if not n:
                continue
            L = int(n.group(1))
            chars = set()
            if "punto (.)" in trozo: chars |= {"."}
            if "coma (,)" in trozo: chars |= {","}
            if "suspensivos" in trozo: chars |= {"…"}
            if "dos puntos" in trozo: chars |= {":"}
            if "¿" in trozo: chars |= set("¿?¡!")
            if "el resto" in trozo: chars |= set(";-–—«»\"“”'‘’()")
            for ch in chars:
                self.signo[ch] = L
        # §6: excepciones
        for c in _filas(t, "## 6.", None):
            for pal in re.split(r",\s*", _limpia(c[1])):
                self.excepcion[pal.lower()] = int(c[0])
        # comprobaciones mínimas
        for clave in ("m", "R_F", "R_S", "ñ", "Y_NEXO"):
            if clave not in self.grafema:
                raise ErrorTabla(f"Falta en la tabla el grafema interno {clave}.")
        if set(self.grupo) != GRUPOS:
            raise ErrorTabla(f"Grupos incompletos: {sorted(GRUPOS - set(self.grupo))}")
        # imprenta de lo que no tiene lección propia (ver D4)
        for k in self.grafema:
            self.imprenta.setdefault(k, 46)


def _base(clave):
    return {"C_K": "c", "C_EI": "c", "G_EI": "g", "R_F": "r", "R_S": "r",
            "Y_CONS": "y", "Y_VOC": "y", "Y_NEXO": "y"}.get(clave, clave)


def cargar_tabla(ruta=None):
    candidatos = [ruta] if ruta else [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "TABLA_PROGRESION.md"),
        "TABLA_PROGRESION.md"]
    for c in candidatos:
        if c and os.path.exists(c):
            return Tabla(open(c, encoding="utf-8").read())
    if ruta:
        raise ErrorTabla(f"No existe {ruta}.")
    with urllib.request.urlopen(URL_TABLA, timeout=15) as r:
        return Tabla(r.read().decode("utf-8"))


# ----------------------------------------------------------------------------
# Análisis de una palabra
# ----------------------------------------------------------------------------
def unidades(palabra):
    """Divide en unidades (tipo, clave). tipo: 'V' vocal, 'C' consonante."""
    w = unicodedata.normalize("NFC", palabra.lower())
    u, i = [], 0
    while i < len(w):
        c = w[i]
        nx = w[i + 1] if i + 1 < len(w) else ""
        nn = w[i + 2] if i + 2 < len(w) else ""
        ant = w[i - 1] if i > 0 else ""
        if c in VOCALES and c != "ü":
            u.append(("V", c)); i += 1; continue
        if w[i:i + 2] in ("ch", "ll", "rr"):
            u.append(("C", w[i:i + 2])); i += 2; continue
        if c == "q":
            if nx == "u" and nn in "eéií" and nn:
                u.append(("C", "qu")); i += 2; continue
            u.append(("C", "q?")); i += 1; continue
        if c == "g" and nx == "u" and nn and nn in "eéií":
            u.append(("C", "gu")); i += 2; continue
        if c == "g" and nx == "ü":
            u.append(("C", "gü")); u.append(("V", "u")); i += 2; continue
        if c == "c":
            u.append(("C", "C_EI" if nx and nx in "eéií" else "C_K")); i += 1; continue
        if c == "g":
            u.append(("C", "G_EI" if nx and nx in "eéií" else "g")); i += 1; continue
        if c == "r":
            if i == 0 or ant in "nls":
                u.append(("C", "R_F"))
            elif ant in VOCALES and nx and nx in VOCALES:
                u.append(("C", "R_S"))
            else:
                u.append(("C", "r"))          # grupo o coda; lo decide la estructura
            i += 1; continue
        if c == "y":
            if w == "y":
                u.append(("C", "Y_NEXO"))
            elif nx and nx in VOCALES:
                u.append(("C", "Y_CONS"))
            else:
                u.append(("V", "Y_VOC"))
            i += 1; continue
        if c == "ü":
            u.append(("V", "u")); i += 1; continue
        u.append(("C", c)); i += 1
    return u


def requisitos(palabra, tabla, imprenta=False):
    """Lista de (lección, motivo) que exige la palabra."""
    lw = unicodedata.normalize("NFC", palabra.lower())
    sin_tilde = lw.translate(ACENTOS)
    req = []

    def pide(clave, motivo, es_grafema=True):
        L = tabla.grafema.get(clave, SIN_LECCION) if es_grafema else clave
        req.append((L, motivo))
        if imprenta and es_grafema and clave in tabla.imprenta:
            req.append((tabla.imprenta[clave], motivo + " (imprenta)"))

    if imprenta:
        req.append((tabla.imprenta.get("V", 1), "vocales (imprenta)"))
    # D1: sílabas especiales como palabra suelta
    if sin_tilde in ("un", "el") and sin_tilde in tabla.especial:
        req.append((tabla.especial[sin_tilde], f"«{sin_tilde}» (sílaba especial)"))
        if imprenta:
            for ch in sin_tilde:
                if ch not in VOCALES:
                    pide(ch, f"letra de «{sin_tilde}»")
        return req
    if sin_tilde == "es" and "es" in tabla.especial:
        req.append((tabla.especial["es"], "«es» (sílaba especial)"))
        if imprenta:
            pide("s", "letra de «es»")
        return req

    if sin_tilde == "y":                                 # nexo
        pide("Y_NEXO", NOMBRE["Y_NEXO"])
        return req

    u = unidades(lw)
    es_inicial = ("es" in tabla.especial and sin_tilde.startswith("es")
                  and len(u) > 2 and u[2][0] == "C")
    for i, (tipo, k) in enumerate(u):
        if tipo == "V":
            if k == "Y_VOC":
                pide("Y_VOC", NOMBRE["Y_VOC"])
            continue
        if k == "q?":
            req.append((SIN_LECCION, "q sin u"))
            continue
        sig = u[i + 1] if i + 1 < len(u) else None
        ant = u[i - 1] if i > 0 else None
        if sig and sig[0] == "V":                       # ataque (inicio de sílaba)
            if ant and ant[0] == "C" and _base(k) in "rl" and (_base(ant[1]) + _base(k)) in GRUPOS:
                gr = _base(ant[1]) + _base(k)
                req.append((tabla.grupo[gr], f"grupo {gr}"))
                if imprenta:
                    pide(ant[1] if ant[1] != "r" else "R_S", f"letra {gr[0]} de {gr}")
                continue
            clave = "R_S" if k == "r" else k
            pide(clave, "grafema " + NOMBRE.get(clave, clave))
        else:                                           # coda o 1.ª de grupo
            if (sig and sig[0] == "C" and i + 2 < len(u) and u[i + 2][0] == "V"
                    and _base(sig[1]) in "rl" and (_base(k) + _base(sig[1])) in GRUPOS):
                continue                                # lo cuenta la 2.ª letra
            b = _base(k)
            if es_inicial and i == 1 and b == "s":
                req.append((tabla.especial["es"], "«es-» (sílaba especial)"))
                continue
            req.append((tabla.coda.get(b, SIN_LECCION), f"{b} a final de sílaba"))
            if imprenta and k in tabla.imprenta:
                req.append((tabla.imprenta[k], f"{b} (imprenta)"))
    # D6: nada queda sin lección; lo que no la tiene se abre con la ortografía completa
    return [(tabla.apertura if L == SIN_LECCION else L, m) for L, m in req]


def leccion_minima(palabra, tabla, imprenta=False):
    r = requisitos(palabra, tabla, imprenta)
    return max([L for L, _ in r], default=1), r


# ----------------------------------------------------------------------------
# Validación de textos
# ----------------------------------------------------------------------------
def validar(texto, leccion, tabla, imprenta=False):
    """Devuelve lista de rechazos: (fragmento, lección requerida, motivos)."""
    rechazos, vistos = [], set()
    texto = unicodedata.normalize("NFC", texto).replace("...", "…")
    for m in re.finditer(rf"[{LETRAS}]+|[^\s{LETRAS}0-9]", texto):
        frag = m.group(0)
        if frag in vistos:
            continue
        vistos.add(frag)
        if re.match(rf"[{LETRAS}]", frag):
            excepcion = tabla.excepcion.get(frag.lower())
            if excepcion is not None and excepcion <= leccion and not imprenta:
                continue
            L, req = leccion_minima(frag, tabla, imprenta)
            if excepcion is not None and excepcion <= leccion and imprenta:
                L = max([x for x, mm in req if "imprenta" in mm] + [excepcion])
                req = [(x, mm) for x, mm in req if "imprenta" in mm]
            if L > leccion:
                motivos = sorted({f"{mm} (L{x})" for x, mm in req if x > leccion})
                rechazos.append((frag, L, motivos))
        else:
            L = tabla.signo.get(frag)
            if L is None:
                rechazos.append((frag, None, ["signo no previsto en la tabla"]))
            elif L > leccion:
                rechazos.append((frag, L, [f"signo «{frag}» (L{L})"]))
    return rechazos


# ----------------------------------------------------------------------------
# Extracción del texto del alumno desde un .tex hecho con la plantilla maestra
# ----------------------------------------------------------------------------
MACROS_ALUMNO = {"bloque": 2, "ficha": 2, "lpalabras": 1, "lfrase": 1, "lparrafo": 1}  # «ficha»: plantillas ≤ v1.2


def _argumentos(tex, pos, n):
    """Lee n argumentos {…} desde pos. Devuelve lista de textos o None."""
    args = []
    for _ in range(n):
        while pos < len(tex) and tex[pos] in " \t\n":
            pos += 1
        if pos >= len(tex) or tex[pos] != "{":
            return None
        nivel, ini = 0, pos
        while pos < len(tex):
            if tex[pos] == "\\":
                pos += 2; continue
            if tex[pos] == "{": nivel += 1
            elif tex[pos] == "}":
                nivel -= 1
                if nivel == 0:
                    break
            pos += 1
        args.append(tex[ini + 1:pos]); pos += 1
    return args


def texto_alumno_tex(tex):
    """Devuelve el texto del alumno contenido en las macros de la plantilla."""
    tex = re.sub(r"(?<!\\)%.*", "", tex)                 # comentarios
    i = tex.find("\\begin{document}")
    cuerpo = tex[i:] if i >= 0 else tex
    trozos = []
    for m in re.finditer(r"\\(bloque|ficha|lpalabras|lfrase|lparrafo)(?![a-zA-Z])", cuerpo):
        n = MACROS_ALUMNO[m.group(1)]
        args = _argumentos(cuerpo, m.end(), n)
        if args is None:
            continue
        t = args[-1]
        t = re.sub(r"\\(ps|char32)\s*", " ", t)          # espacios con pauta
        t = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", t)  # otras órdenes
        t = t.replace("{", " ").replace("}", " ").replace("~", " ")
        if m.group(1) == "lpalabras":
            t = t.replace(",", " ")                       # la coma separa, no se lee
        trozos.append(t)
    return "\n".join(trozos)


def inventario(leccion, tabla):
    g = sorted([k for k, v in tabla.grafema.items() if v <= leccion],
               key=lambda k: tabla.grafema[k])
    return {
        "grafemas": ["vocales"] + [NOMBRE.get(k, k) for k in g],
        "especiales": [k for k, v in tabla.especial.items() if v <= leccion],
        "codas": sorted(k for k, v in tabla.coda.items() if v <= leccion),
        "grupos": sorted(k for k, v in tabla.grupo.items() if v <= leccion),
        "excepciones": sorted(k for k, v in tabla.excepcion.items() if v <= leccion),
        "signos": "".join(sorted(k for k, v in tabla.signo.items() if v <= leccion)),
        "ortografia_completa": leccion >= tabla.apertura,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-l", "--leccion", type=int, help="lección alcanzada (1–72)")
    ap.add_argument("-f", "--fichero", help="archivo de texto con el vocabulario o las frases")
    ap.add_argument("--tex", help="archivo .tex hecho con la plantilla maestra (valida solo el texto del alumno)")
    ap.add_argument("--imprenta", action="store_true", help="el texto irá en letra de imprenta")
    ap.add_argument("--tabla", help="ruta de TABLA_PROGRESION.md (por defecto, junto al script o en GitHub)")
    ap.add_argument("--explicar", action="store_true", help="muestra el análisis de cada palabra")
    ap.add_argument("--inventario", type=int, metavar="L", help="lista lo admitido en la lección L")
    ap.add_argument("palabras", nargs="*")
    a = ap.parse_args()
    try:
        tabla = cargar_tabla(a.tabla)
    except ErrorTabla as e:
        print(f"ERROR EN LA TABLA: {e}", file=sys.stderr); return 2
    if a.inventario:
        for k, v in inventario(a.inventario, tabla).items():
            print(f"{k:20} {', '.join(v) if isinstance(v, list) else v}")
        return 0
    if not a.leccion:
        ap.error("falta la lección (-l)")
    texto = " ".join(a.palabras)
    if a.fichero:
        texto += "\n" + open(a.fichero, encoding="utf-8").read()
    if a.tex:
        extraido = texto_alumno_tex(open(a.tex, encoding="utf-8").read())
        if not extraido.strip():
            print("ERROR: el .tex no contiene texto del alumno en \\bloque, \\lpalabras, \\lfrase ni \\lparrafo.",
                  file=sys.stderr)
            return 2
        texto += "\n" + extraido
    if a.explicar:
        for w in dict.fromkeys(re.findall(rf"[{LETRAS}]+", texto)):
            L, req = leccion_minima(w, tabla, a.imprenta)
            print(f"{w:18} L{L:<3} " + "; ".join(f"{m} L{x}" for x, m in req))
        return 0
    rechazos = validar(texto, a.leccion, tabla, a.imprenta)
    modo = "imprenta" if a.imprenta else "ligada"
    if not rechazos:
        print(f"VALIDACIÓN SUPERADA — lección {a.leccion}, {modo}.")
        return 0
    print(f"VALIDACIÓN NO SUPERADA — lección {a.leccion}, {modo}. Rechazos:")
    for frag, L, motivos in rechazos:
        cuando = f"requiere L{L}" if L else "no admitido"
        print(f"  ✗ {frag:16} {cuando:14} {'; '.join(motivos)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
