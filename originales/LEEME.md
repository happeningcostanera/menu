# Originales de la carta

Aca van los tres archivos de Illustrator, exportados a PDF. Cada uno se
convierte solo en las hojas de la carta: **una mesa de trabajo, una hoja**.

No hay que exportar los JPG a mano ni contar hojas. Si la carta de vinos
pasa de 19 a 22 hojas, se sube el PDF nuevo y listo.

## Como se tienen que llamar

No importan mayusculas, acentos, espacios, guiones ni palabras de mas.
Lo unico que importa es que el nombre contenga la palabra de su seccion:

| seccion  | palabra que tiene que aparecer          | ejemplos que funcionan          |
|----------|-----------------------------------------|---------------------------------|
| espanol  | `espanol`, `castellano` o `menu`        | `Gardiner Carta Espanol.pdf`    |
| ingles   | `ingles` o `english`                    | `GARDINER_INGLES_final.pdf`     |
| vinos    | `vinos`                                 | `Carta de Vinos 2026.pdf`       |

**No mezclar palabras de dos secciones.** `Vinos en Ingles.pdf` no se
puede resolver: avisa y no hace nada, para no mandarlo a la carpeta
equivocada.

Si un archivo no se reconoce, queda anotado en la pestana **Actions** de
GitHub. Nunca se ignora en silencio.

## Al exportar desde Illustrator

Archivo -> Guardar como -> Adobe PDF. Solo tres cosas importan:

1. **Mesas de trabajo: Todas.** Si no, sale un PDF de una sola pagina.
2. **Revisar el orden de las mesas de trabajo.** Es el orden en que van a
   quedar las hojas (Ventana -> Mesas de trabajo).
3. **Destildar "Conservar funciones de edicion de Illustrator".** Viene
   tildada y mete el .ai entero adentro del PDF, duplicando el peso.

Lo demas da igual: las marcas de corte y el sangrado se recortan solos, y
el CMYK se convierte al renderizar.

Un .ai tambien sirve, si se guardo con "Crear archivo PDF compatible".
