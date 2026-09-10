#!/usr/bin/env python3
"""Banco de pruebas del validador. Uso: python3 test_validador.py"""
import sys
from validador_grafemas import cargar_tabla, leccion_minima, validar
T = cargar_tabla()
# (palabra, lección mínima en ligada, por qué)
CASOS = [
    ("mamá", 2, "m + tilde libre (D3)"), ("Mimí", 2, "mayúscula ligada con su minúscula (D4)"),
    ("oía", 1, "hiato, solo vocales (D2)"), ("auto", 3, "diptongo libre + t"),
    ("es", 3, "sílaba especial (D1)"), ("este", 3, "es- inicial (D1)"), ("está", 3, "es- inicial + tilde"),
    ("un", 4, "especial (D1)"), ("una", 4, "u-na, sin inversa"), ("el", 6, "especial"), ("él", 6, "equivale a el (D3)"),
    ("tiene", 4, "diptongo ie"), ("peine", 5, ""), ("duele", 7, ""),
    ("esposa", 8, "es- inicial + s en ataque"), ("mesa", 8, ""),
    ("rueda", 9, "r inicial fuerte"), ("perro", 9, "rr"), ("pera", 35, "r suave intervocálica"),
    ("honra", 47, "r fuerte tras n, pero n en coda"), ("Enrique", 47, "n en coda, qu L32"),
    ("hueso", 11, "h"), ("ahí", 11, "h intercalada"),
    ("bota", 24, ""), ("llave", 25, ""), ("yema", 26, "y consonante"), ("rey", 26, "y final"),
    ("hoy", 26, "y final"), ("y", 26, "nexo"), ("desayunado", 26, "de-sa-yu-na-do"),
    ("leche", 27, "ch"), ("foto", 28, ""), ("cena", 29, "c ante e"), ("zapato", 29, ""),
    ("gitano", 30, "g ante i"), ("jefe", 30, ""), ("gato", 31, "g ante a"), ("guerra", 31, "gu ante e + rr"),
    ("agua", 31, "g ante u + diptongo"), ("casa", 32, "c ante a"), ("queso", 32, ""),
    ("taxi", 33, "x"), ("niño", 34, "ñ"), ("cigüeña", 72, "gü sin lección → apertura (D6)"),
    ("pingüino", 72, "gü + n en coda"), ("kilo", 72, "k sin lección"), ("reloj", 72, "coda j sin lección"),
    ("asno", 46, "coda s"), ("antes", 47, "coda n"), ("arco", 48, "coda r"), ("alto", 49, "coda l"),
    ("campo", 50, "coda m"), ("pez", 53, "coda z"), ("pared", 57, "coda d"),
    ("texto", 63, "coda x"), ("recto", 63, "coda c"), ("absoluto", 64, "coda b"), ("atleta", 64, "at-le-ta: coda t, no grupo"),
    ("tren", 65, "grupo tr + coda n"), ("madre", 66, "dr"), ("libro", 67, "br"), ("globo", 68, "gl"),
    ("flor", 69, "fl"), ("plato", 70, "pl"), ("clavo", 71, "cl"), ("estrella", 65, "es- + tr"),
    ("instante", 47, "ns-tan: codas n y s"), ("obstáculo", 64, "codas b y s"),
    ("examen", 47, "x entre vocales L33, n final L47"), ("médico", 32, ""), ("farmacia", 48, "coda r"),
]
fallos = 0
for w, esperado, nota in CASOS:
    L, req = leccion_minima(w, T)
    if L != esperado:
        fallos += 1
        print(f"FALLO {w}: da L{L}, esperado L{esperado} ({nota}) → {req}")
# Validación de textos y excepciones
pruebas_texto = [
    ("Mi mamá toma té.", 3, True), ("Mi mamá toma té.", 2, False),
    ("¿Te dio Ana la moneda?", 23, True), ("¿Te dio Ana la moneda?", 22, False),
    ("Me hace daño el pie.", 29, True), ("La niña tiene sueño.", 29, False),   # daño es excepción, niña no
    ("Vimos un mochuelo.", 27, True), ("Tenemos un mochuelo.", 27, False),  # vimos sí, tenemos no
    ("Hola, Pili, pasa a la sala.", 22, True),
]
for texto, L, ok in pruebas_texto:
    r = validar(texto, L, T)
    if (not r) != ok:
        fallos += 1
        print(f"FALLO texto «{texto}» en L{L}: esperado {'admitido' if ok else 'rechazado'} → {r}")
# Imprenta
for w, L, ok in [("mamá", 12, False), ("mamá", 13, True), ("bota", 24, False), ("bota", 36, True),
                 ("niño", 34, False), ("niño", 46, True), ("pera", 35, False), ("pera", 46, True)]:
    r = validar(w, L, T, imprenta=True)
    if (not r) != ok:
        fallos += 1
        print(f"FALLO imprenta «{w}» en L{L}: esperado {'admitido' if ok else 'rechazado'} → {r}")
total = len(CASOS) + len(pruebas_texto) + 8
print(f"{total - fallos}/{total} pruebas superadas.")
sys.exit(1 if fallos else 0)
