# Plan de llenado de carton box

Página estática con las instrucciones de cubicaje para las 7 referencias de caja
en carton box de 120 × 80 × 70 cm.

## Contenido

| Fichero | Para qué sirve |
|---|---|
| `index.html` | La página. Un solo fichero, sin dependencias (los dibujos son SVG embebido). |
| `.nojekyll` | Evita que GitHub Pages procese el sitio con Jekyll. No lo borres. |
| `robots.txt` | Pide a Google y otros buscadores que no indexen la página. |

## Publicar en GitHub Pages (desde el navegador, sin instalar nada)

1. En **github.com**, arriba a la derecha: **+ → New repository**.
2. Nombre, por ejemplo `cubicaje-cajas`. Déjalo **Public** y crea el repositorio.
   - Con una cuenta Free, GitHub Pages solo funciona en repositorios públicos.
     Si necesitas que sea privado, hace falta GitHub Pro / Team.
3. En el repositorio vacío: **uploading an existing file**.
4. Arrastra los tres ficheros de esta carpeta (`index.html`, `.nojekyll`, `robots.txt`)
   y pulsa **Commit changes**.
5. **Settings → Pages**. En *Source* elige **Deploy from a branch**;
   en *Branch*, `main` y carpeta `/ (root)`. **Save**.
6. Al minuto o dos aparece la URL arriba en esa misma pantalla:
   `https://TU-USUARIO.github.io/cubicaje-cajas/`

Esa es la dirección que puedes enviar a cualquiera, dentro o fuera de la organización.

## Para actualizar la página

Sube un `index.html` nuevo al repositorio (GitHub te pregunta si quieres
reemplazar el existente). El cambio se publica solo, en la misma URL.

## Antes de publicar, ten en cuenta

- Un repositorio público significa **página pública**: cualquiera con el enlace
  la ve, y el enlace es adivinable. `robots.txt` y la etiqueta `noindex`
  reducen la visibilidad en buscadores, pero no son un control de acceso.
- La página contiene medidas de producto y volúmenes de campaña. Si eso es
  información sensible para tu organización, no la publiques en un repositorio
  público: usa un repositorio privado con GitHub Pro, o envía el fichero
  `index.html` por email.

## Nota técnica

Las cantidades por carton box salen de un solver de bin packing 3D
(corte guillotina recursivo con memoización, evaluando las 6 orientaciones de
cada caja y desempatando por el plan con menos bloques, para que sea explicable
en el almacén). Todas las soluciones se han verificado por código: ninguna caja
se solapa y ninguna sobresale de los 120 × 80 × 70 cm.
