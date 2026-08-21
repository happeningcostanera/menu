"""
Comprime las hojas de la carta para que carguen rapido en el telefono.

Lo corre GitHub solo, cada vez que alguien sube una imagen.
Nadie tiene que acordarse de nada: se sube la hoja como siempre
y un minuto despues queda liviana.

Si alguna vez queres que se vean con mas definicion, subi ANCHO_MAX.
"""
from PIL import Image, ImageOps
from pathlib import Path

CARPETAS   = ['menu', 'vinos', 'ingles']   # 'logo' queda afuera a proposito
ANCHO_MAX  = 2400      # px de ancho para las hojas que alguien sube a mano.
                       # Tiene que ser >= al ANCHO_MAX de hojas-desde-pdf.py,
                       # o este achicaria lo que aquel genera y se anularian.
LIMITE_KB  = 900       # una hoja mas pesada que esto se recomprime

# Dos calidades a proposito:
# - si la hoja hay que achicarla, viene con detalle de sobra y aguanta 82
# - si ya es chica, no hay nada que ahorrar: se guarda casi intacta,
#   porque los pocos KB que ganariamos no valen perder definicion
CALIDAD_ACHICADA = 82
CALIDAD_INTACTA  = 92


def hay_que_tocarla(peso_bytes, im):
    """Decide si la hoja necesita trabajo. Si ya esta bien, no se toca:
       asi una imagen no se recomprime una y otra vez perdiendo calidad."""
    if im.mode != 'RGB':                    # CMYK de imprenta -> la web no lo quiere
        return 'era CMYK'
    if im.width > ANCHO_MAX:                # mas grande de lo que se llega a ver
        return 'muy ancha'
    if peso_bytes > LIMITE_KB * 1024:       # liviana de tamano pero pesada de peso
        return 'muy pesada'
    return None


def main():
    tocadas = 0
    ilegibles = []

    for carpeta in CARPETAS:
        d = Path(carpeta)
        if not d.is_dir():
            continue

        for p in sorted(d.iterdir()):
            if p.suffix.lower() not in ('.jpg', '.jpeg'):
                continue

            antes = p.stat().st_size

            try:
                im = Image.open(p)
                im.load()
            except Exception as e:
                # Un archivo roto o que no es una imagen no puede frenar todo
                # el proceso: se avisa, se lo deja quieto y se sigue.
                print(f'  OJO   {p}  no se pudo leer ({e.__class__.__name__}), se saltea')
                ilegibles.append(p)
                continue

            with im:
                motivo = hay_que_tocarla(antes, im)
                if not motivo:
                    print(f'  ok    {p}  ({antes // 1024} KB)')
                    continue
                # exif_transpose respeta la rotacion de la foto antes de
                # guardarla, porque al guardar se pierden los datos EXIF
                nueva = ImageOps.exif_transpose(im).convert('RGB')
                se_achica = nueva.width > ANCHO_MAX
                if se_achica:
                    nueva.thumbnail((ANCHO_MAX, ANCHO_MAX * 20), Image.LANCZOS)

            calidad = CALIDAD_ACHICADA if se_achica else CALIDAD_INTACTA
            nueva.save(p, 'JPEG', quality=calidad, optimize=True, progressive=True)
            despues = p.stat().st_size
            tocadas += 1
            print(f'  ---> {p}  {antes // 1024} KB -> {despues // 1024} KB  ({motivo})')

    print(f'\n{tocadas} hoja(s) comprimida(s).')
    if ilegibles:
        print(f'{len(ilegibles)} archivo(s) sin poder leer: ' + ', '.join(str(p) for p in ilegibles))
        print('Si alguno deberia ser una hoja de la carta, hay que volver a subirlo.')


if __name__ == '__main__':
    main()
