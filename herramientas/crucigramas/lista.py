"""Lista cerrada de palabras para las cruzadas con pictogramas.

Cada palabra lleva el identificador de su pictograma de ARASAAC, revisado a mano uno a uno
(octubre de 2026). Test de inclusión: un adulto que no ve la palabra diría exactamente esa
palabra al ver el dibujo. Para añadir una palabra: revisar su pictograma en blanco y negro,
comprobar que no lleva texto ni flechas y que no se confunde con otra de la lista.
"""

PALABRAS = {
    # Casa y hogar
    'casa': 2317, 'mesa': 3129, 'silla': 3155, 'sofá': 25479, 'cama': 2304, 'puerta': 3244,
    'ventana': 2611, 'llave': 8153, 'lámpara': 4936, 'reloj': 2549, 'espejo': 8573,
    'armario': 2258, 'nevera': 4876, 'lavadora': 2442, 'horno': 2426, 'teléfono': 2791,
    'ordenador': 7190, 'bañera': 2272, 'ducha': 2370, 'toalla': 2593, 'jabón': 25171,
    'peine': 2852, 'escoba': 2745, 'cubo': 2725, 'plancha': 2528, 'vaso': 2610,
    'plato': 2532, 'taza': 2582, 'cuchara': 2362, 'tenedor': 2588, 'cuchillo': 3237,
    'sartén': 2558, 'olla': 9086, 'botella': 2288, 'bolsa': 27616, 'grifo': 3339,
    # Comida
    'pan': 2494, 'leche': 2445, 'queso': 2541, 'tomate': 2594, 'lechuga': 2446,
    'cebolla': 2323, 'zanahoria': 2619, 'plátano': 2530, 'manzana': 2462, 'naranja': 2483,
    'pera': 2561, 'uvas': 3247, 'piña': 2525, 'fresa': 2400, 'limón': 3022, 'pollo': 4952,
    'pizza': 2527, 'helado': 2420, 'tarta': 2579, 'paella': 5532, 'sopa': 2573,
    'jamón': 2433,
    # Ropa y complementos
    'camisa': 2308, 'camiseta': 2309, 'pantalón': 2565, 'falda': 2391, 'vestido': 2613,
    'zapato': 32923, 'bota': 8299, 'calcetín': 8339, 'gorra': 2411, 'sombrero': 2572,
    'bufanda': 2290, 'guante': 8353, 'gafas': 3329, 'bolso': 2284, 'paraguas': 2500,
    'pijama': 2522, 'cinturón': 2336, 'corbata': 2716,
    # Transporte y calle
    'coche': 6981, 'moto': 2480, 'autobús': 26654, 'tren': 7282, 'avión': 2264,
    'barco': 2273, 'bicicleta': 2277, 'camión': 6956, 'semáforo': 2567,
    # Naturaleza
    'árbol': 3057, 'flor': 3102, 'sol': 2798, 'estrella': 4644, 'fuego': 4654,
    'montaña': 2909,
    # Animales
    'perro': 2517, 'gato': 2406, 'caballo': 2294, 'vaca': 2609, 'cerdo': 2327,
    'oveja': 2489, 'gallina': 2403, 'pato': 2563, 'pez': 2520, 'pájaro': 2490,
    'conejo': 2351, 'ratón': 2546, 'burro': 2291, 'león': 2449, 'elefante': 2372,
    'jirafa': 2437, 'mono': 2477, 'abeja': 24823, 'mariposa': 2465, 'caracol': 8061,
    'tortuga': 2596, 'serpiente': 2568, 'oso': 2488,
    # Profesiones
    'médico': 2467, 'policía': 5547, 'bombero': 2664, 'camarero': 2681, 'cocinero': 6985,
    'peluquera': 11333, 'cartero': 2690, 'panadero': 3358,
    # Objetos
    'libro': 2450, 'lápiz': 2440, 'tijeras': 2591, 'maleta': 2931, 'mochila': 2475,
    'vela': 6242, 'globo': 8313, 'pelota': 3241, 'guitarra': 2417, 'tambor': 2578,
    'martillo': 2922, 'escalera': 2743, 'regalo': 25381, 'caja': 5935, 'bombilla': 2285,
    'radio': 11354, 'jarabe': 2962, 'termómetro': 2789, 'tirita': 8331, 'silbato': 6182,
    'candado': 6957,
    # Cuerpo
    'mano': 2928, 'pie': 2841, 'ojo': 6573, 'boca': 2663, 'nariz': 2887, 'oreja': 2871,
}

# Palabras que no pueden ir en la misma cruzada (dibujos o palabras que se confunden).
CONFLICTOS = [
    {'pez', 'pescado'}, {'caballo', 'burro'}, {'botella', 'jarabe'}, {'caja', 'regalo'},
    {'llave', 'candado'}, {'pollo', 'gallina'}, {'naranja', 'limón'}, {'guante', 'mano'},
    {'pan', 'panadero'}, {'cuchara', 'jarabe'}, {'pájaro', 'gallina', 'pato'}, {'vaso', 'leche'},
    {'zapato', 'bota'}, {'camisa', 'camiseta'}, {'gorra', 'sombrero'}, {'taza', 'vaso'},
    {'policía', 'semáforo'}, {'pie', 'calcetín'}, {'escoba', 'cubo'},
    {'bolso', 'bolsa', 'mochila'}, {'rata', 'ratón'}, {'tren', 'metro'},
]

# Retoques de pictogramas: (recorte x0, y0, x1, y1 sobre el PNG de 500 px, quitar línea del suelo)
RETOQUES = {
    'policía': ((0, 0, 347, 500), True),     # el 5547 lleva un semáforo a la derecha
}

PICTO_ENUNCIADO = 2380                         # accion_escribir (mano escribiendo)


def nombre(palabra):
    """Nombre de archivo sin tildes ni ñ."""
    return palabra.translate(str.maketrans('áéíóúüñ', 'aeiouun'))


def en_conflicto(palabra, seleccion):
    return any(palabra in C and (C - {palabra}) & set(seleccion) for C in CONFLICTOS)


def cargar_extra(ruta):
    """Palabras añadidas: una por línea, «palabra id_arasaac». Líneas con # se ignoran."""
    extra = {}
    for linea in open(ruta, encoding='utf-8'):
        linea = linea.split('#')[0].strip()
        if linea:
            w, i = linea.split(); extra[w] = int(i)
    return extra
