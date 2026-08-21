"""
Convierte los originales de Illustrator en las hojas sueltas de la carta.

Se sube UN archivo por seccion a la carpeta originales/ y este script abre
cada uno, renderiza cada mesa de trabajo como un JPG con el nombre que la
carta espera, y borra las hojas que dejaron de existir.

Asi la cantidad de hojas deja de ser algo que hay que mantener a mano:
es, literalmente, la cantidad de mesas de trabajo del archivo.

Acepta .pdf y tambien .ai, siempre que el .ai se haya guardado con la
opcion "Crear archivo PDF compatible" (viene tildada por defecto).
"""
import hashlib
import json
import re
import statistics
import unicodedata
from pathlib import Path

import pymupdf

ORIGINALES = Path('originales')
# El ancho de cada hoja NO es fijo: se calcula para que el texto reciba
# siempre la misma cantidad de pixeles por letra.
#
# Si una hoja tiene la letra mas chica que otra, al mismo ancho recibe
# menos pixeles por letra y se ve mas blanda al lado de las demas.
# Calculando el ancho hoja por hoja, todas quedan parejas.
OBJETIVO_PX = 35       # alto en pixeles del cuerpo de texto
ANCHO_MIN   = 1200
ANCHO_MAX   = 2400     # tope, por si alguna hoja tiene la letra diminuta
CALIDAD    = 82
# Que cuenta como titulo de seccion. Se calibra solo contra cada archivo,
# porque no todas las cartas usan la misma escala: en Gardiner los titulos
# miden 2.8 veces el cuerpo y en Happening 1.6, asi que un umbral fijo
# funcionaba en una y en la otra no encontraba ninguno.
PROPORCION_TITULO = 0.9    # del texto mas grande de todo el documento
MINIMO_SOBRE_CUERPO = 1.25 # y ademas tiene que destacarse en su propia hoja
REGISTRO   = ORIGINALES / 'procesado.json'   # que version de cada original ya se convirtio
MANIFIESTO = Path('secciones.json')          # titulos de cada hoja, para los accesos directos

# Son tres archivos de Illustrator distintos: espanol, ingles y vinos.
#
# origen  : como se llama la seccion (para los mensajes y el registro)
# alias   : palabras que identifican la seccion sin lugar a dudas
# debiles : palabras genericas, que solo valen si ningun alias fuerte
#           acerto. 'carta' esta aca porque los tres archivos son cartas:
#           "Carta de Vinos" tiene que ir a vinos, no al espanol.
# destino : en que carpeta van las hojas
# nombre  : como se llama cada hoja (n = numero de mesa de trabajo)
SECCIONES = [
    {'origen': 'menu',   'destino': 'menu',   'nombre': lambda n: f'h55-{n:02d}',
     'alias': ['menu', 'espanol', 'español', 'castellano', 'es'],
     'debiles': ['carta', 'happening', 'h55']},

    {'origen': 'ingles', 'destino': 'ingles', 'nombre': lambda n: f'h55_en-{n:02d}',
     'alias': ['ingles', 'inglés', 'english', 'en'],
     'debiles': []},

    {'origen': 'vinos',  'destino': 'vinos',  'nombre': lambda n: f'h55_vinos-{n:02d}',
     'alias': ['vinos', 'vino', 'wines', 'carta-de-vinos', 'cartadevinos'],
     'debiles': []},
]

EXTENSIONES = ('.pdf', '.ai')


def es_original(p):
    return p.is_file() and p.suffix.lower() in EXTENSIONES


def normalizar(texto):
    """'Gardiner Carta Espanol 2026' -> 'gardinercartaespanol2026'

    Saca acentos, espacios, guiones y mayusculas, para que el nombre del
    archivo pueda ser el que Illustrator haya puesto sin que importe.
    """
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', texto.lower())


def a_que_seccion_pertenece(p):
    """Devuelve la seccion de ese archivo, o None si no se puede saber.

    Va en tres pasadas, de lo mas seguro a lo mas flojo:
      1. nombre exacto             'vinos.pdf'
      2. contiene una palabra clave 'Gardiner - Vinos 2026.pdf'
      3. contiene una generica      'Carta Gardiner.pdf' -> espanol

    Las claves cortas como 'es' o 'en' solo valen en la pasada 1, porque
    si no 'ingles' contendria 'es' y seria un lio.
    """
    stem = normalizar(p.stem)

    def contiene(palabras):
        return [sec for sec in SECCIONES
                if any(len(a) >= 4 and normalizar(a) in stem for a in sec[palabras])]

    for sec in SECCIONES:
        if stem in {normalizar(a) for a in sec['alias']}:
            return sec

    for palabras in ('alias', 'debiles'):
        encontradas = contiene(palabras)
        if len(encontradas) == 1:
            return encontradas[0]
        if len(encontradas) > 1:
            return None    # ambigua de verdad: mejor avisar que adivinar

    return None


def buscar_original(sec):
    """Devuelve el archivo original de esa seccion, o None si no se subio."""
    for p in sorted(ORIGINALES.iterdir()):
        if es_original(p) and a_que_seccion_pertenece(p) is sec:
            return p
    return None


def avisar_de_los_no_reconocidos(usados):
    """Un PDF con el nombre mal puesto no puede pasar desapercibido."""
    sueltos = [p for p in sorted(ORIGINALES.iterdir()) if es_original(p) and p not in usados]
    if not sueltos:
        return
    print('\nOJO: estos archivos estan en originales/ pero no se reconocieron:')
    for p in sueltos:
        print(f'   {p.name}')
    print('Los nombres aceptados son:')
    for sec in SECCIONES:
        print(f"   {sec['destino']:8} -> " + ', '.join(sec['alias'] + sec['debiles']))


def huella(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def leer_registro():
    try:
        return json.loads(REGISTRO.read_text())
    except Exception:
        return {}


def hojas_existentes(sec):
    """Las hojas que hoy hay en la carpeta destino y siguen el patron de nombres.

    Se arma comparando contra los nombres que este script genera, para no
    tocar jamas un archivo que haya puesto alguien a mano con otro nombre.
    """
    carpeta = Path(sec['destino'])
    if not carpeta.is_dir():
        return {}

    esperados = {}
    for n in range(1, 500):
        esperados[sec['nombre'](n)] = n

    encontradas = {}
    for p in carpeta.iterdir():
        if p.suffix.lower() in ('.jpg', '.jpeg') and p.stem in esperados:
            encontradas[esperados[p.stem]] = p
    return encontradas


def parece_espaciado(texto):
    """'B E B I D A S  Y' -> True.  'Vinos Blancos' -> False.

    Algunos titulos se componen separando las letras. Al extraer el texto
    queda un espacio entre cada una y se pierde donde termina la palabra."""
    piezas = texto.split()
    return len(piezas) >= 4 and sum(1 for p in piezas if len(p) == 1) / len(piezas) >= 0.6


def reparar_espaciado(chars):
    """Rehace las palabras midiendo el hueco entre letra y letra.

    El espaciado entre letras de una misma palabra es parejo; el corte de
    palabra deja un hueco bastante mayor. Se usa eso para separarlas."""
    ls = [(c['c'], c['bbox'][0], c['bbox'][2]) for c in chars if c['c'].strip()]
    if len(ls) < 2:
        return ''.join(c for c, _, _ in ls)
    huecos = [ls[i+1][1] - ls[i][2] for i in range(len(ls)-1)]
    normal = statistics.median(huecos)
    salida = ls[0][0]
    for i, h in enumerate(huecos):
        if h > normal * 1.8:
            salida += ' '
        salida += ls[i+1][0]
    return salida


def titulos_de(pagina, corte):
    """Titulos de seccion de una hoja: [(texto, altura relativa 0..1), ...]

    Solo se repara el espaciado de los titulos que lo necesitan: aplicarlo
    a todos rompe los que ya venian bien, porque en una tipografia con
    mucho ajuste entre pares los huecos normales ya son irregulares."""
    spans = [s
             for b in pagina.get_text('rawdict')['blocks']
             for l in b.get('lines', [])
             for s in l['spans'] if s.get('chars')]
    if not spans:
        return []

    cuerpo = statistics.median([s['size'] for s in spans])

    grandes = []
    for s in spans:
        if s['size'] < corte or s['size'] < cuerpo * MINIMO_SOBRE_CUERPO:
            continue
        crudo = ''.join(c['c'] for c in s['chars'])
        texto = reparar_espaciado(s['chars']) if parece_espaciado(crudo) else crudo
        texto = ' '.join(texto.split())
        if texto:
            grandes.append((texto, s['bbox'][0], s['bbox'][2], s['bbox'][1], s['size']))

    grandes.sort(key=lambda g: (round(g[3] / 4), g[1]))

    # 1) juntar fragmentos del mismo renglon, pero solo si estan pegados:
    #    dos titulos pueden compartir renglon en columnas distintas
    renglones = []
    for texto, x0, x1, y, tam in grandes:
        if renglones:
            ant = renglones[-1]
            mismo_alto = abs(y - ant['y']) <= 4
            hueco = x0 - ant['x1']
            # el hueco tiene que ser chico Y hacia adelante: si es negativo
            # el fragmento esta en otra columna, no es el mismo titulo
            cerca = 0 <= hueco < tam * 1.5
            if mismo_alto and cerca:
                ant['partes'].append(texto); ant['x1'] = x1
                continue
        renglones.append({'partes': [texto], 'x0': x0, 'x1': x1, 'y': y, 'tam': tam})

    # 2) juntar renglones seguidos que son un mismo titulo partido en dos
    unidos = []
    for r in renglones:
        if unidos:
            ant = unidos[-1]
            if (r['y'] - ant['y']) < ant['tam'] * 1.6 and r['x0'] < ant['x1'] and r['x1'] > ant['x0']:
                ant['partes'].extend(r['partes']); ant['y'] = ant['y']
                continue
        unidos.append(dict(r))

    salida = []
    for r in unidos:
        texto = ' '.join(' '.join(r['partes']).split())
        if len(texto) >= 3:
            rel = (r['y'] - pagina.rect.y0) / pagina.rect.height
            salida.append((texto, round(max(0.0, min(1.0, rel)), 4)))
    return salida


def escribir_manifiesto():
    """Deja en secciones.json los titulos de cada hoja, para que la carta
       pueda armar los accesos directos sin que nadie los escriba a mano."""
    hojas, titulos = [], []
    for sec in SECCIONES:
        original = buscar_original(sec)
        if original is None:
            continue
        doc = pymupdf.open(original)

        # el corte se calcula con todo el documento, no hoja por hoja
        medidas = [s['size']
                   for pg in doc
                   for b in pg.get_text('dict')['blocks']
                   for l in b.get('lines', [])
                   for s in l['spans'] if s['text'].strip()]
        corte = max(medidas) * PROPORCION_TITULO if medidas else 0

        numero = 0
        for pagina in doc:
            recorte = pymupdf.Rect(pagina.trimbox)
            if recorte.is_valid and not recorte.is_empty and recorte != pagina.rect:
                pagina.set_cropbox(recorte)
            if not pagina.get_text().strip():
                continue                      # mesa vacia: se salteo al convertir
            numero += 1

            # las medidas son las mismas que salieron al convertir, porque
            # el ancho se calcula igual; sirven para reservar el espacio en
            # la pagina antes de que la imagen llegue a cargarse
            ancho = ancho_para(pagina)
            zoom = ancho / pagina.rect.width
            # irect es como el propio motor redondea al rasterizar; calcularlo
            # a mano daba 1 px de diferencia en el alto
            caja = (pagina.rect * pymupdf.Matrix(zoom, zoom)).irect
            hojas.append({'carpeta': sec['destino'], 'hoja': numero,
                          'ancho': caja.width, 'alto': caja.height})

            for texto, y in titulos_de(pagina, corte):
                titulos.append({'carpeta': sec['destino'], 'hoja': numero,
                                'titulo': texto, 'y': y})
        doc.close()

    MANIFIESTO.write_text(
        json.dumps({'hojas': hojas, 'titulos': titulos}, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    print(f'\n{MANIFIESTO}: {len(hojas)} hojas, {len(titulos)} accesos directos')
    for m in titulos:
        print(f"   {m['carpeta']}/{m['hoja']:<3} {m['y']:.2f}  {m['titulo']}")


def ancho_para(pagina):
    """Ancho en px para que el cuerpo de texto de esta hoja mida OBJETIVO_PX.

    Se usa la mediana del tamano de letra, que representa el texto corrido
    y no se deja arrastrar por un titulo grande o una nota al pie chica.
    """
    tam = [s['size']
           for b in pagina.get_text('dict')['blocks']
           for l in b.get('lines', [])
           for s in l['spans'] if s['text'].strip()]

    if not tam:
        return ANCHO_MIN
    mediana = statistics.median(tam)
    ideal = OBJETIVO_PX / mediana * pagina.rect.width
    return round(min(ANCHO_MAX, max(ANCHO_MIN, ideal)))


def convertir(sec, original):
    carpeta = Path(sec['destino'])
    carpeta.mkdir(exist_ok=True)

    doc = pymupdf.open(original)
    print(f"  {original}  ->  {doc.page_count} mesa(s) de trabajo")

    generadas = set()
    numero = 0                 # cuenta solo las hojas que de verdad se publican
    for i, pagina in enumerate(doc, start=1):
        # Si el PDF se exporto con sangrado y marcas de corte, la hoja de
        # verdad es el TrimBox: recortando ahi, las marcas y el margen
        # sobrante no llegan a la carta aunque nadie apague esa opcion.
        recorte = pymupdf.Rect(pagina.trimbox)
        if recorte.is_valid and not recorte.is_empty and recorte != pagina.rect:
            pagina.set_cropbox(recorte)
            print(f'     hoja {i:2d}  tenia sangrado, se recorta al tamano final')

        ancho = ancho_para(pagina)
        zoom = ancho / pagina.rect.width
        pix = pagina.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csRGB)

        # Una mesa de trabajo vacia no tiene que salir como hoja en blanco.
        # Se saltea sin gastar numero, asi la numeracion no deja huecos.
        if not any(b != 255 for b in pix.samples):
            print(f'     mesa {i:2d}  esta vacia, se saltea')
            continue

        numero += 1
        destino = carpeta / (sec['nombre'](numero) + '.jpg')
        pix.pil_save(destino, format='JPEG', quality=CALIDAD, optimize=True, progressive=True)

        generadas.add(numero)
        print(f"     hoja {numero:2d}  ->  {destino}  ({destino.stat().st_size // 1024} KB, {pix.width}x{pix.height})")

    doc.close()

    # las hojas que sobraron ya no estan en el original: se van
    for numero, p in sorted(hojas_existentes(sec).items()):
        if numero not in generadas:
            print(f"     sobra   ->  {p}  (ya no esta en el original, se borra)")
            p.unlink()

    return len(generadas)


def main():
    if not ORIGINALES.is_dir():
        print('No hay carpeta originales/. No hay nada que convertir.')
        return

    registro = leer_registro()
    nuevo = dict(registro)
    trabajo = False
    usados = []

    for sec in SECCIONES:
        original = buscar_original(sec)
        if original is not None:
            usados.append(original)

        if original is None:
            # Sin original no se toca la carpeta. Es a proposito: si alguien
            # borra el PDF por error, las hojas que ya estan siguen ahi.
            print(f"  {sec['origen']}: no hay original, se deja como esta")
            continue

        h = huella(original)
        if registro.get(sec['origen']) == h:
            print(f"  {sec['origen']}: sin cambios desde la ultima vez")
            continue

        convertir(sec, original)
        nuevo[sec['origen']] = h
        trabajo = True

    if trabajo:
        REGISTRO.write_text(json.dumps(nuevo, indent=2, sort_keys=True) + '\n')
        print('\nHojas regeneradas.')
    else:
        print('\nNada para hacer.')

    # El manifiesto se rehace siempre, aunque no haya habido conversion:
    # es barato (solo lee texto) y asi nunca queda desfasado de las hojas.
    escribir_manifiesto()
    avisar_de_los_no_reconocidos(usados)


if __name__ == '__main__':
    main()
