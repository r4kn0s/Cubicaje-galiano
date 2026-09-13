# Cubicaje Galiano

Plan de cubicaje y llenado de **carton box 120 × 80 × 100 cm** para las siete referencias
de caja de la campaña, más el análisis económico de carton box frente a palet flejado.

**Página publicada:** https://r4kn0s.github.io/Cubicaje-galiano/

---

## Qué hay aquí

| Archivo | Qué es |
|---|---|
| `index.html` | La página. Es un archivo autocontenido (CSS y SVG embebidos); es lo que sirve GitHub Pages. **Generado — no editar a mano.** |
| `cubicaje.py` | El cálculo y el generador de la página. Aquí se cambian las medidas y las cantidades. |
| `estilo.css` | Hoja de estilos. `cubicaje.py` la incrusta en `index.html` al generar. |
| `datos.json` | Los planes calculados (zonas, bloques, orientaciones, alturas) por si se quieren consumir desde otro sitio. |

## Cómo regenerar la página

```bash
python3 cubicaje.py
```

Sin dependencias: solo la librería estándar de Python 3. Escribe `index.html` y `datos.json`.
Después, commit y push: GitHub Pages publica sola.

Para cambiar el cálculo, editar las constantes del principio de `cubicaje.py`:

```python
CARTON_BOX_EXT = (1200, 800, 1000)   # medidas exteriores del box, mm
MERMA_POR_CARA = 10                  # grosor de cartón descontado por cara, mm
CAJAS      = {"B1": (364, 279, 42), ...}   # largo × ancho × alto, mm
CANTIDADES = {"B1": 40000, ...}
```

El espacio útil sale de restar la merma: **118 × 78 × 98 cm**.

## Resultado actual

| Ref | Caja (cm) | Cajas/box | Pasos | Carton box | Volumen aprovechado |
|---|---|---|---|---|---|
| B1 | 36,4 × 27,9 × 4,2 | 204 | 6 | 197 | 96,5 % |
| B2 | 36,4 × 27,9 × 9,2 | 80 | 2 | 163 | 82,9 % |
| B3 | 36,4 × 26,4 × 13,7 | 59 | 5 | 45 | 86,1 % |
| D1 | 47,4 × 36,9 × 8,7 | 54 | 4 | 91 | 91,1 % |
| D-1 | 47,4 × 36,9 × 5,7 | 86 | 4 | 303 | 95,1 % |
| G | 63,4 × 51,4 × 8,2 | 28 | 5 | 286 | 83,0 % |
| J | 70,4 × 49,4 × 10,2 | 19 | 2 | 395 | 74,7 % |

**102.000 cajas en 1.480 carton box.** Con el patrón intuitivo de solo cajas planas harían
falta 1.542: combinar planas, de canto y de pie ahorra 62 boxes.

## Cómo se calcula

Es un problema de *3D bin packing* (container loading, variante **single bin size, single
item type**). `cubicaje.py` hace una búsqueda exhaustiva sobre:

1. las **6 orientaciones** de cada caja;
2. todas las **divisiones del suelo del box** en zonas mediante cortes guillotina
   (hasta 3 zonas), con normalización a puntos raster para recortar el espacio inútil;
3. todas las **combinaciones de bloques apilados** en altura dentro de cada zona.

El resultado coincide con el óptimo de una búsqueda guillotina completa en profundidad 10
para las siete referencias, y se eligió el modelo por zonas porque produce planes que una
persona puede seguir: cada paso es una rejilla uniforme repetida N pisos.

Cada solución se **verifica** antes de publicarse: ninguna caja sale del box y ninguna
solapa con otra (comprobación par a par de los 204 / 86 / … paralelepípedos).

## Limitaciones

El cálculo es puramente geométrico. **No** incluye:

- peso máximo por box ni por palet;
- resistencia al apilado (aplastamiento) de las cajas de abajo;
- refuerzos o esquineras interiores que reduzcan la huella útil;
- restricciones de «este lado arriba» — el plan usa cajas de canto y de pie.

Conviene montar un box piloto de cada referencia antes de lanzar la serie.

## Análisis económico

La pestaña **«Box o fleje»** de la página compara dos configuraciones reales:

- **A** — columna de dos carton box con palet debajo y otro entre medias (2,288 m;
  2 boxes × 12 € + 2 palets × 7 € = 38 €).
- **B** — palet flejado progresivamente según se apila hasta 2,00 m totales
  (1 palet + fleje ≈ 9 €).

Conclusión: el fleje gana en coste en las siete referencias, pero **B1** (44 capas planas
de 4,2 cm) y **D-1** (32 capas, esbeltez 6,5) no son flejeables en la práctica y son
justamente donde el box sale más barato por caja (5,6 y 9,1 céntimos). La política mixta
—box para B1 y D-1, fleje para el resto— ahorra unos 11.850 € netos.

Si cambian los precios, están todos juntos en la constante `DECISION` de `cubicaje.py`.
