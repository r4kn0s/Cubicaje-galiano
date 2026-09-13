# -*- coding: utf-8 -*-
"""
Cubicaje Galiano
================
Calcula el numero maximo de cajas de cada referencia que caben en un carton box
y genera 'index.html' con las fichas de llenado paso a paso.

Uso:   python3 cubicaje.py
Salida: index.html  +  datos.json

El problema es un 3D bin packing (container loading, single bin / single item type).
Se resuelve con una busqueda exhaustiva sobre:
  - las 6 orientaciones de la caja,
  - todas las divisiones en zonas del suelo del box (cortes guillotina),
  - todas las combinaciones de bloques apilados en altura (knapsack).
Cada solucion se verifica: ninguna caja sale del box y ninguna solapa con otra.
"""
import itertools, json, math, html, os, sys

# ---------------------------------------------------------------- parametros
CARTON_BOX_EXT = (1200, 800, 1000)   # medidas exteriores del carton box, mm
MERMA_POR_CARA = 10                  # grosor de carton descontado en cada cara, mm

CAJAS = {                            # largo x ancho x alto, mm
    "B1":  (364, 279,  42),
    "B2":  (364, 279,  92),
    "B3":  (364, 264, 137),
    "D1":  (474, 369,  87),
    "D-1": (474, 369,  57),
    "G":   (634, 514,  82),
    "J":   (704, 494, 102),
}
CANTIDADES = {
    "B1": 40000, "B2": 13000, "B3": 2600, "D1": 4871,
    "D-1": 26029, "G": 8000, "J": 7500,
}
ORDEN = ["B1", "B2", "B3", "D1", "D-1", "G", "J"]

CL = CARTON_BOX_EXT[0] - 2 * MERMA_POR_CARA
CW = CARTON_BOX_EXT[1] - 2 * MERMA_POR_CARA
CH = CARTON_BOX_EXT[2] - 2 * MERMA_POR_CARA

ZONAS = "ABCDEFG"
C30 = math.cos(math.radians(30))

# ---------------------------------------------------------------- utilidades
def raster(dims, limite):
    """Posiciones alcanzables como suma de multiplos de dims."""
    alc = [False] * (limite + 1)
    alc[0] = True
    for v in range(limite + 1):
        if alc[v]:
            for d in dims:
                if v + d <= limite:
                    alc[v + d] = True
    return [i for i in range(limite + 1) if alc[i]]

def tabla_norm(r, limite):
    """Para cada v, el mayor punto raster <= v (permite recortar el espacio inutil)."""
    t = [0] * (limite + 1)
    j = c = 0
    for v in range(limite + 1):
        while j < len(r) and r[j] <= v:
            c = r[j]
            j += 1
        t[v] = c
    return t

def cm(mm):
    s = "%.1f" % (mm / 10.0)
    if s.endswith(".0"):
        s = s[:-2]
    return s.replace(".", ",")

def miles(n):
    return format(n, ",d").replace(",", ".")

# ---------------------------------------------------------------- optimizador
def bloque_apilado(L, W, dims, max_bloques=2):
    """Mejor pila de hasta `max_bloques` bloques homogeneos dentro de L x W x CH.
    Un bloque = una orientacion + rejilla nx*ny + k pisos."""
    orients = sorted(set(itertools.permutations(dims)))
    mejor = [0, None]

    def rec(h_libre, bloques, total, prof):
        if total > mejor[0]:
            mejor[0], mejor[1] = total, list(bloques)
        if prof == 0:
            return
        for o in orients:
            a, b, c = o
            if a > L or b > W or c > h_libre:
                continue
            por_piso = (L // a) * (W // b)
            for k in range(h_libre // c, 0, -1):
                bloques.append((o, L // a, W // b, k))
                rec(h_libre - k * c, bloques, total + por_piso * k, prof - 1)
                bloques.pop()

    rec(CH, [], 0, max_bloques)
    return mejor[0], mejor[1]

def optimizar(dims, prof_zonas=2):
    """Divide el suelo en zonas (cortes guillotina) y apila bloques en cada zona."""
    ds = sorted(set(dims))
    rx, ry = raster(ds, CL), raster(ds, CW)
    memo = {}

    def reg(L, W, prof):
        clave = (L, W, prof)
        if clave in memo:
            return memo[clave]
        n, bl = bloque_apilado(L, W, dims)
        mejor = (n, {"t": "zona", "L": L, "W": W, "bloques": bl})
        if prof > 0:
            for x in rx:
                if x <= 0:
                    continue
                if 2 * x > L:
                    break
                r1, r2 = reg(x, W, prof - 1), reg(L - x, W, prof - 1)
                if r1[0] + r2[0] > mejor[0]:
                    mejor = (r1[0] + r2[0], {"t": "X", "at": x, "A": r1[1], "B": r2[1]})
            for y in ry:
                if y <= 0:
                    continue
                if 2 * y > W:
                    break
                r1, r2 = reg(L, y, prof - 1), reg(L, W - y, prof - 1)
                if r1[0] + r2[0] > mejor[0]:
                    mejor = (r1[0] + r2[0], {"t": "Y", "at": y, "A": r1[1], "B": r2[1]})
        memo[clave] = mejor
        return mejor

    return reg(CL, CW, prof_zonas)

def recolectar(plan, ox, oy, zonas):
    if plan["t"] == "zona":
        zonas.append((ox, oy, plan["L"], plan["W"], plan["bloques"]))
    elif plan["t"] == "X":
        recolectar(plan["A"], ox, oy, zonas)
        recolectar(plan["B"], ox + plan["at"], oy, zonas)
    else:
        recolectar(plan["A"], ox, oy, zonas)
        recolectar(plan["B"], ox, oy + plan["at"], zonas)

def postura(orient, original):
    L0, W0, H0 = original
    c = orient[2]
    if c == H0:
        return "PLANA", "tal cual viene, con la tapa arriba"
    if c == W0:
        return "DE CANTO", "de perfil, como carpetas en un archivador"
    return "DE PIE", "levantada, apoyada en su lado corto"

def solapan(p, q):
    for i in range(3):
        if p[i] + p[i + 3] <= q[i] or q[i] + q[i + 3] <= p[i]:
            return False
    return True

def plan_referencia(ref):
    dims = CAJAS[ref]
    n, arbol = optimizar(dims)
    crudas = []
    recolectar(arbol, 0, 0, crudas)
    zonas, colocadas = [], []
    for i, (ox, oy, L, W, bloques) in enumerate(crudas):
        z = 0
        bl = []
        for (o, nx, ny, k) in bloques:
            a, b, c = o
            p, ayuda = postura(o, dims)
            for kk in range(k):
                for jj in range(ny):
                    for ii in range(nx):
                        colocadas.append((ox + ii * a, oy + jj * b, z + kk * c, a, b, c))
            bl.append({"w": a, "d": b, "h": c, "nx": nx, "ny": ny, "layers": k,
                       "z0": z, "z1": z + k * c, "n": nx * ny * k,
                       "pose": p, "posedesc": ayuda})
            z += k * c
        zonas.append({"id": ZONAS[i], "x": ox, "y": oy, "L": L, "W": W,
                      "n": sum(b["n"] for b in bl), "blocks": bl})

    # ---- verificacion
    assert len(colocadas) == n, (ref, len(colocadas), n)
    for q in colocadas:
        assert q[0] >= 0 and q[1] >= 0 and q[2] >= 0
        assert q[0] + q[3] <= CL and q[1] + q[4] <= CW and q[2] + q[5] <= CH, (ref, q)
        assert sorted(q[3:6]) == sorted(dims), (ref, q)
    for i in range(len(colocadas)):
        for j in range(i + 1, len(colocadas)):
            assert not solapan(colocadas[i], colocadas[j]), (ref, i, j)

    vol = dims[0] * dims[1] * dims[2]
    q = CANTIDADES[ref]
    return {"dims": list(dims), "n": n, "qty": q, "boxes": -(-q // n),
            "last": q - (-(-q // n) - 1) * n, "zones": zonas,
            "fill": round(100.0 * n * vol / (CL * CW * CH), 1),
            "ubvol": (CL * CW * CH) // vol}

# ================================================================ dibujos SVG
def iso_conjunto(pasos):
    """Vista isometrica del box lleno. Proyeccion: x hacia abajo-derecha,
    y hacia abajo-izquierda, z hacia arriba; escala 0,30 px/mm."""
    s, pad = 0.30, 26
    ox, oy = pad + C30 * s * CW, pad + s * CH
    W = C30 * s * (CL + CW) + 2 * pad
    H = oy + 0.5 * s * (CL + CW) + pad
    P = lambda X, Y, Z: (ox + C30 * s * (X - Y), oy + 0.5 * s * (X + Y) - s * Z)
    lin = lambda a, b: '<polyline class="wire" points="%.1f,%.1f %.1f,%.1f"/>' % (a[0], a[1], b[0], b[1])
    o = []
    O, X1, Y1, Z1 = P(0, 0, 0), P(CL, 0, 0), P(0, CW, 0), P(0, 0, CH)
    for a, b in ((O, X1), (O, Y1), (O, Z1), (X1, P(CL, 0, CH)), (Y1, P(0, CW, CH)),
                 (Z1, P(CL, 0, CH)), (Z1, P(0, CW, CH))):
        o.append(lin(a, b))
    cajas = []
    for i, st in enumerate(pasos):
        for (X, Y, Z, a, b, c) in st["place"]:
            cajas.append((X + Y + Z, X, Y, Z, a, b, c, i % 5))
    cajas.sort(key=lambda t: t[0])          # painter: lo lejano primero
    for (_, X, Y, Z, a, b, c, sh) in cajas:
        t  = [P(X, Y, Z + c), P(X + a, Y, Z + c), P(X + a, Y + b, Z + c), P(X, Y + b, Z + c)]
        fx = [P(X + a, Y, Z + c), P(X + a, Y + b, Z + c), P(X + a, Y + b, Z), P(X + a, Y, Z)]
        fy = [P(X, Y + b, Z + c), P(X + a, Y + b, Z + c), P(X + a, Y + b, Z), P(X, Y + b, Z)]
        for cls, poly in (("fx", fx), ("fy", fy), ("ft", t)):
            o.append('<polygon class="%s s%d" points="%s"/>' %
                     (cls, sh, " ".join("%.1f,%.1f" % p for p in poly)))
    return ('<svg viewBox="0 0 %.0f %.0f" class="dwg" role="img" '
            'aria-label="Vista en 3D del carton box lleno">%s</svg>' % (W, H, "".join(o)))

def alzado(pasos):
    k, m = 0.34, 32
    W, H = CL * k + 2 * m + 46, CH * k + 2 * m
    o = ['<rect class="cont" x="%d" y="%d" width="%.1f" height="%.1f"/>' % (m, m, CL * k, CH * k)]
    for i, st in enumerate(pasos):
        for (X, Y, Z, a, b, c) in st["place"]:
            o.append('<rect class="cell-done s%d" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
                     % (i % 5, m + X * k, m + (CH - (Z + c)) * k, a * k, c * k))
    usadas = []
    for z1 in sorted({st["z1"] for st in pasos}, reverse=True):
        y = m + (CH - z1) * k
        if any(abs(y - u) < 14 for u in usadas):
            continue
        usadas.append(y)
        o.append('<path class="lvl" d="M %d %.1f L %.1f %.1f"/>' % (m - 8, y, m + CL * k + 10, y))
        o.append('<text class="lvln" x="%.1f" y="%.1f">%s cm</text>' % (m + CL * k + 14, y + 4, cm(z1)))
    o.append('<text class="cap" x="%d" y="%.1f">Frente del box &#183; %s cm de ancho</text>'
             % (m, m + CH * k + 22, cm(CL)))
    return ('<svg viewBox="0 0 %.0f %.0f" class="dwg" role="img" '
            'aria-label="Alzado con las alturas de cada piso">%s</svg>' % (W, H, "".join(o)))

def planta(pasos, idx):
    k, m = 0.42, 34
    W, H = CL * k + 2 * m, CW * k + 2 * m + 26
    st = pasos[idx]; z, b = st["zone"], st["blk"]
    o = ['<defs><marker id="ah" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" '
         'markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" '
         'fill="var(--signal)"/></marker></defs>',
         '<rect class="cont" x="%d" y="%d" width="%.1f" height="%.1f"/>' % (m, m, CL * k, CW * k)]
    for pi in range(idx):
        for (X, Y, Z, a, bb, c) in pasos[pi]["place"]:
            o.append('<rect class="cell-done s%d" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
                     % (pi % 5, m + X * k, m + Y * k, a * k, bb * k))
    for j in range(b["ny"]):
        for i in range(b["nx"]):
            o.append('<rect class="cell-new s%d" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
                     % (idx % 5, m + (z["x"] + i * b["w"]) * k, m + (z["y"] + j * b["d"]) * k,
                        b["w"] * k, b["d"] * k))
    o.append('<rect class="zone" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
             % (m + z["x"] * k, m + z["y"] * k, z["L"] * k, z["W"] * k))
    sx = m + (z["x"] + b["w"] * 0.5) * k
    sy = m + (z["y"] + b["d"] * 0.5) * k
    if b["nx"] >= b["ny"]:
        ex, ey = m + (z["x"] + b["nx"] * b["w"] - b["w"] * 0.5) * k, sy
    else:
        ex, ey = sx, m + (z["y"] + b["ny"] * b["d"] - b["d"] * 0.5) * k
    if abs(ex - sx) + abs(ey - sy) > 26:
        o.append('<path class="arrow" d="M %.1f %.1f L %.1f %.1f"/>' % (sx, sy, ex, ey))
    o.append('<circle class="startdot" cx="%.1f" cy="%.1f" r="11"/>' % (sx, sy))
    o.append('<text class="startn" x="%.1f" y="%.1f" text-anchor="middle">%d</text>' % (sx, sy + 4, idx + 1))
    o.append('<text class="dim" x="%.1f" y="%d" text-anchor="middle">%s cm de largo</text>'
             % (m + CL * k / 2, m - 12, cm(CL)))
    o.append('<text class="cap" x="%d" y="%.1f">Visto desde arriba &#183; %s cm de fondo</text>'
             % (m, m + CW * k + 22, cm(CW)))
    return ('<svg viewBox="0 0 %.0f %.0f" class="dwg" role="img" '
            'aria-label="Planta del paso %d">%s</svg>' % (W, H, idx + 1, "".join(o)))

def caja_suelta(b):
    a, d, c = b["w"], b["d"], b["h"]
    s = 250.0 / max(C30 * (a + d), 0.5 * (a + d) + c)
    etq = "%s alto" % cm(c)
    padL = 18 + len(etq) * 9.0
    padR = 22 + max(len(cm(a)), len(cm(d))) * 9.0
    padT, padB = 26, 38
    ox, oy = padL + C30 * s * d, padT + s * c
    W = C30 * s * (a + d) + padL + padR
    H = oy + 0.5 * s * (a + d) + padB
    P = lambda X, Y, Z: (ox + C30 * s * (X - Y), oy + 0.5 * s * (X + Y) - s * Z)
    t  = [P(0, 0, c), P(a, 0, c), P(a, d, c), P(0, d, c)]
    fx = [P(a, 0, c), P(a, d, c), P(a, d, 0), P(a, 0, 0)]
    fy = [P(0, d, c), P(a, d, c), P(a, d, 0), P(0, d, 0)]
    ymax = max(p[1] for p in fx + fy)
    o = ['<path class="floor" d="M %.1f %.1f L %.1f %.1f"/>'
         % (max(4, padL * 0.35), ymax + 11, W - max(4, padR * 0.35), ymax + 11)]
    for cls, poly in (("fx", fx), ("fy", fy), ("ft", t)):
        o.append('<polygon class="%s" points="%s"/>' % (cls, " ".join("%.1f,%.1f" % p for p in poly)))
    p0, p1 = P(0, 0, c), P(a, 0, c)
    o.append('<text class="elab" x="%.1f" y="%.1f" text-anchor="start">%s</text>'
             % ((p0[0] + p1[0]) / 2 + 4, (p0[1] + p1[1]) / 2 - 8, cm(a)))
    q0, q1 = P(a, 0, 0), P(a, d, 0)
    o.append('<text class="elab" x="%.1f" y="%.1f" text-anchor="start">%s</text>'
             % ((q0[0] + q1[0]) / 2 + 10, (q0[1] + q1[1]) / 2 + 15, cm(d)))
    r0, r1 = P(0, d, 0), P(0, d, c)
    o.append('<text class="elab hi" x="%.1f" y="%.1f" text-anchor="end">%s</text>'
             % (r0[0] - 12, (r0[1] + r1[1]) / 2 + 4, etq))
    o.append('<text class="cap" x="6" y="%.1f">Medidas en cm</text>' % (H - 8))
    return ('<svg viewBox="0 0 %.0f %.0f" class="dwg onebox" role="img" '
            'aria-label="Orientacion de la caja en este paso">%s</svg>' % (W, H, "".join(o)))

# =============================================================== pagina HTML
CLASE_POSTURA = {"PLANA": "p-plana", "DE CANTO": "p-canto", "DE PIE": "p-pie"}

# Analisis economico: carton box doble frente a palet flejado a 2 m.
# Precios: box 12 EUR, palet 7 EUR, fleje+film 2 EUR, posicion de suelo 30 EUR (estimada).
DECISION = [
    ("B1",  "6,6", "44", "408", "352", "0,167", "0,111", "0,60 &#8364;",  "BOX"),
    ("B2",  "3,0", "20", "160", "160", "0,425", "0,244", "ni gratis",     "FLEJE"),
    ("B3",  "1,9", "13", "118", "117", "0,576", "0,333", "ni gratis",     "FLEJE"),
    ("D1",  "4,2", "21", "108",  "84", "0,630", "0,464", "3,07 &#8364;",  "FLEJE"),
    ("D-1", "6,5", "32", "172", "128", "0,395", "0,305", "4,20 &#8364;",  "BOX"),
    ("G",   "6,3", "22",  "56",  "44", "1,214", "0,886", "2,82 &#8364;",  "FLEJE"),
    ("J",   "4,8", "18",  "38",  "36", "1,789", "1,083", "ni gratis",     "FLEJE"),
]

def zona_texto(z, varias):
    if not varias:
        return "Ocupa todo el suelo del box."
    partes = []
    if z["x"] == 0 and z["x"] + z["L"] >= CL:
        partes.append("todo el largo")
    elif z["x"] == 0:
        partes.append("desde el borde izquierdo hasta %s cm" % cm(z["L"]))
    else:
        partes.append("desde %s cm hasta %s cm de largo" % (cm(z["x"]), cm(z["x"] + z["L"])))
    if z["y"] == 0 and z["y"] + z["W"] >= CW:
        partes.append("todo el fondo")
    elif z["y"] == 0:
        partes.append("desde el frente hasta %s cm de fondo" % cm(z["W"]))
    else:
        partes.append("desde %s cm hasta %s cm de fondo" % (cm(z["y"]), cm(z["y"] + z["W"])))
    return "Zona marcada en naranja: %s." % (" y ".join(partes))

def pasos_de(v):
    pasos = []
    for z in v["zones"]:
        for b in z["blocks"]:
            place = []
            for kk in range(b["layers"]):
                for j in range(b["ny"]):
                    for i in range(b["nx"]):
                        place.append((z["x"] + i * b["w"], z["y"] + j * b["d"],
                                      b["z0"] + kk * b["h"], b["w"], b["d"], b["h"]))
            pasos.append({"zone": z, "blk": b, "place": place,
                          "z0": b["z0"], "z1": b["z1"], "n": b["n"]})
    return pasos

def ficha(ref, v):
    pasos = pasos_de(v)
    varias = len(v["zones"]) > 1
    s = ['<section class="ref" id="ref-%s" role="tabpanel" aria-labelledby="tab-%s" hidden>' % (ref, ref)]
    s.append('<header class="ref-hd"><div class="ref-id"><p class="eyebrow">Referencia</p>'
             '<h2>%s</h2><p class="dimline">Caja de %s &#215; %s &#215; %s cm</p></div>'
             '<div class="target"><span class="tv">%d</span>'
             '<span class="tl">cajas en cada<br>carton box</span></div></header>'
             % (html.escape(ref), cm(v["dims"][0]), cm(v["dims"][1]), cm(v["dims"][2]), v["n"]))
    s.append('<div class="views"><figure><figcaption>As&#237; queda al terminar</figcaption>%s</figure>'
             '<figure><figcaption>Alturas de cada piso</figcaption>%s</figure></div>'
             % (iso_conjunto(pasos), alzado(pasos)))
    s.append('<p class="sub">Orden de llenado &#8212; %d pasos</p><ol class="steps">' % len(pasos))
    for i, st in enumerate(pasos):
        b, z = st["blk"], st["zone"]
        rep = ', repetido en <b>%d alturas</b>' % b["layers"] if b["layers"] > 1 else ''
        s.append('<li class="step"><div class="step-hd"><span class="stepno">%d</span>'
                 '<span class="stepcount">%d cajas</span><span class="pose %s">%s</span>'
                 '<span class="posehelp">%s</span></div>'
                 '<div class="step-body"><div class="step-plan">%s</div>'
                 '<div class="step-side"><div class="obox">%s</div><ul class="instr">'
                 '<li>Apoya la caja sobre la cara de <b>%s &#215; %s cm</b>. Queda con <b>%s cm de alto</b>.</li>'
                 '<li>Coloca <b>%d a lo largo &#215; %d en fondo</b>%s.</li>'
                 '<li>%s</li>'
                 '<li>Empieza por el punto <span class="inline-dot">%d</span> y avanza en la direcci&#243;n de la flecha.</li>'
                 '<li>Este piso va de <b>%s cm</b> a <b>%s cm</b> de altura.</li>'
                 '</ul></div></div></li>'
                 % (i + 1, st["n"], CLASE_POSTURA[b["pose"]], b["pose"], b["posedesc"],
                    planta(pasos, i), caja_suelta(b),
                    cm(b["w"]), cm(b["d"]), cm(b["h"]),
                    b["nx"], b["ny"], rep, zona_texto(z, varias), i + 1,
                    cm(b["z0"]), cm(b["z1"])))
    s.append('</ol><p class="check">Comprueba antes de cerrar: deben quedar <b>%d cajas</b> dentro. '
             'Si sobran o faltan, revisa el paso donde se torci&#243;.</p></section>' % v["n"])
    return "".join(s)

def seccion_decision():
    filas = "".join(
        '<tr><th scope="row">%s</th><td class="num">%s</td><td class="num">%s</td>'
        '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td>'
        '<td class="num">%s</td><td class="num big">%s</td><td class="num">%s</td>'
        '<td><b>%s</b></td></tr>'
        % (r, "%s &#215; %s &#215; %s" % (cm(CAJAS[r][0]), cm(CAJAS[r][1]), cm(CAJAS[r][2])),
           esb, cap, A, B, ca, cb, pm, dec)
        for (r, esb, cap, A, B, ca, cb, pm, dec) in DECISION)
    return """<section id="decision" role="tabpanel" aria-labelledby="tab-decision" hidden>
  <header class="ref-hd">
    <div class="ref-id"><p class="eyebrow">An&#225;lisis econ&#243;mico</p>
      <h2>Carton box<br>o palet flejado</h2>
      <p class="dimline">Box 12 &#8364; &#183; palet 7 &#8364; &#183; fleje 2 &#8364;</p></div>
    <div class="target"><span class="tv">11.850&#8364;</span>
      <span class="tl">de ahorro con<br>la pol&#237;tica mixta</span></div>
  </header>
  <p class="lede" style="margin-top:0">Comparaci&#243;n de las dos configuraciones reales: <b>A</b>, columna de dos
  carton box con un palet debajo y otro entre medias (2,288 m; 2 boxes + 2 palets = 38 &#8364;), frente a <b>B</b>,
  palet flejado progresivamente seg&#250;n se apila hasta 2,00 m totales (1 palet + fleje &#8776; 9 &#8364;).</p>

  <h3>El criterio espacial que decide</h3>
  <p class="note" style="margin-top:4px">Son tres pruebas geom&#233;tricas, en este orden.</p>
  <ul class="rules">
    <li><b>Esbeltez de la caja</b> &#8212; alto &#247; lado menor de la cara que apoya, en sus orientaciones no planas.
      Si pasa de ~2, el fleje solo puede apilarla <b>plana</b>, y entonces el box es la &#250;nica forma de usarla de
      canto o de pie. Ah&#237; es donde el box compra densidad de verdad.</li>
    <li><b>N&#250;mero de capas planas en 2 m</b> &#8212; 1.856 &#247; alto. Por encima de unas 30 capas el mont&#243;n
      telescopia y se abre por el centro aunque lo flejes seg&#250;n subes. Eso no lo arregla el fleje: o box, o
      bandeja intermedia.</li>
    <li><b>Teselado de la huella</b> &#8212; cajas por capa &#215; superficie que cubren del 120 &#215; 80. Si la caja
      no tesela el palet, el hueco es de formato y no lo corrige ninguna de las dos opciones.</li>
  </ul>
  <p class="note">Las tres se resumen en un solo n&#250;mero comparable:
  <b>coste por caja = (embalaje + posici&#243;n de suelo) &#247; cajas por posici&#243;n de suelo</b>.</p>

  <div class="tablewrap" style="margin-top:18px">
    <table style="min-width:780px">
      <caption>Coste por caja seg&#250;n configuraci&#243;n</caption>
      <thead><tr><th scope="col">Ref</th><th scope="col">Caja (cm)</th><th scope="col">Esbeltez</th>
        <th scope="col">Capas en 2 m</th><th scope="col">A: 2 box</th><th scope="col">B: fleje 2 m</th>
        <th scope="col">&#8364;/caja A</th><th scope="col">&#8364;/caja B</th>
        <th scope="col">M&#225;ximo que podr&#237;a costar el box</th><th scope="col">Decisi&#243;n</th></tr></thead>
      <tbody>__FILAS__</tbody>
    </table>
  </div>
  <p class="note">&#171;A&#187; y &#171;B&#187; son cajas por posici&#243;n de suelo. La columna en naranja es siempre
  la opci&#243;n m&#225;s barata. &#218;nica cifra estimada: <b>30 &#8364; por posici&#243;n de suelo</b> en
  cami&#243;n; con el dato real se recalcula en un minuto.</p>

  <h3>La mejor opci&#243;n</h3>
  <p class="note" style="margin-top:4px;font-size:16px;color:var(--ink)"><b>El fleje a 2 m gana en las siete
  referencias sobre coste puro.</b> Material: 7.848 &#8364; contra 28.234 &#8364;. Cuesta 129 posiciones de suelo
  m&#225;s (872 contra 743), pero el fleje seguir&#237;a ganando aunque una posici&#243;n costara hasta
  <b>158 &#8364;</b>, y no vale ni la quinta parte de eso. Coste total estimado: <b>34.008 &#8364;</b> contra
  <b>50.524 &#8364;</b>.</p>
  <p class="note">Lo que mata a la opci&#243;n A no es solo el box: es que la columna doble <b>gasta dos palets</b>
  (14 &#8364;) contra uno. Por eso en B2, B3 y J el box no se justifica <b>ni siendo gratis</b> &#8212; aporta 0,
  &#8722;1 y +2 cajas por posici&#243;n, y eso no paga ni el segundo palet.</p>

  <p class="check">Pero hay dos referencias donde no aplicar&#237;a el fleje, y no por dinero.
  <b>B1: 44 capas.</b> Ocho cajas de 4,2 cm por capa, 44 pisos, 1,85 m. Eso no es un palet, es una torre de naipes;
  se abre por el centro aunque flejes cada tres capas. Y es donde el box sale m&#225;s barato de todas:
  <b>5,6 c&#233;ntimos por caja</b> de sobrecoste. <b>D-1: 32 capas</b> y esbeltez 6,5; adem&#225;s el box gana
  44 cajas por posici&#243;n (172 contra 128) porque puede ponerlas de canto, que el fleje no puede. Sobrecoste:
  <b>9,1 c&#233;ntimos por caja</b>.</p>

  <h3>Recomendaci&#243;n</h3>
  <div class="tablewrap" style="margin-top:8px">
    <table>
      <caption>Pol&#237;tica mixta</caption>
      <thead><tr><th scope="col">Configuraci&#243;n</th><th scope="col">Referencias</th>
        <th scope="col">Cajas</th><th scope="col">Unidades de carga</th></tr></thead>
      <tbody>
        <tr><th scope="row" style="font-size:17px">Doble carton box<br>+ palet intermedio</th>
          <td><b>B1, D-1</b></td><td class="num">66.029</td><td class="num">251 columnas (99 + 152)</td></tr>
        <tr><th scope="row" style="font-size:17px">Palet flejado<br>a 2 m</th>
          <td><b>B2, B3, D1, G, J</b></td><td class="num">35.971</td><td class="num">549 palets</td></tr>
      </tbody>
    </table>
  </div>
  <p class="note">Ahorra <b>unos 11.850 &#8364; netos</b> frente a meter todo en box, y deja el box solo donde compra
  algo que el fleje no puede dar. Llevar tambi&#233;n B1 y D-1 a fleje a&#241;adir&#237;a otros 4.666 &#8364;, y es
  exactamente donde no lo har&#237;a: se lo come el cart&#243;n aplastado y los recuentos.</p>
  <p class="note">Dos cosas m&#225;s, por si abren decisi&#243;n. Si se acepta palet intermedio sobre carga flejada,
  B1 y D-1 podr&#237;an ir en dos tramos flejados de 1 m y se ahorrar&#237;an esos 4.666 &#8364; &#8212; pero apoyar
  un palet cargado sobre 17 capas de cart&#243;n de 5,7 cm es precisamente lo que el box evita. Y <b>G y J tienen un
  problema de formato, no de m&#233;todo</b>: con solo 2 cajas por capa cubren el 68 % y el 72 % de la huella del
  palet, y ni el box ni el fleje lo arreglan.</p>
</section>""".replace("__FILAS__", filas)

TABS_JS = """(function(){
  var tabs=[].slice.call(document.querySelectorAll('.tab'));
  function show(t){
    tabs.forEach(function(b){
      var sel=(b===t);
      b.setAttribute('aria-selected',sel?'true':'false');
      document.getElementById(b.getAttribute('aria-controls')).hidden=!sel;
    });
    if(history.replaceState) history.replaceState(null,'','#'+t.getAttribute('aria-controls'));
  }
  tabs.forEach(function(b){
    b.addEventListener('click',function(){show(b);window.scrollTo({top:0,behavior:'instant'});});
    b.addEventListener('keydown',function(e){
      var i=tabs.indexOf(b),n=null;
      if(e.key==='ArrowRight')n=tabs[(i+1)%tabs.length];
      if(e.key==='ArrowLeft')n=tabs[(i-1+tabs.length)%tabs.length];
      if(n){e.preventDefault();n.focus();show(n);}
    });
  });
  var h=location.hash.replace('#','');
  var start=tabs.filter(function(b){return b.getAttribute('aria-controls')===h;})[0];
  show(start||tabs[0]);
})();"""

def generar():
    datos, fichas, filas = {}, [], ""
    tq = tbx = 0
    for ref in ORDEN:
        v = plan_referencia(ref)
        datos[ref] = v
        n_pasos = sum(len(z["blocks"]) for z in v["zones"])
        tq += v["qty"]; tbx += v["boxes"]
        filas += ('<tr><th scope="row">%s</th><td class="num">%s&#215;%s&#215;%s</td>'
                  '<td class="num big">%d</td><td class="num">%d</td><td class="num">%s</td></tr>'
                  % (html.escape(ref), cm(v["dims"][0]), cm(v["dims"][1]), cm(v["dims"][2]),
                     v["n"], n_pasos, miles(v["boxes"])))
        fichas.append(ficha(ref, v))
        print("  %-4s %3d cajas/box  %d pasos  %s carton box  %.1f %% de volumen"
              % (ref, v["n"], n_pasos, miles(v["boxes"]), v["fill"]))

    tabs = ('<button class="tab" id="tab-resumen" role="tab" aria-selected="true" '
            'aria-controls="resumen">Resumen</button>'
            '<button class="tab" id="tab-decision" role="tab" aria-selected="false" '
            'aria-controls="decision">Box o fleje</button>'
            + "".join('<button class="tab" id="tab-%s" role="tab" aria-selected="false" '
                      'aria-controls="ref-%s">%s</button>' % (r, r, html.escape(r)) for r in ORDEN))

    css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "estilo.css"),
               encoding="utf-8").read()

    doc = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Plan de llenado &#8212; Carton box %(ext)s</title>
<meta name="description" content="Plan de cubicaje y orden de llenado de carton box para las 7 referencias de caja, con el analisis de carton box frente a palet flejado.">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
%(css)s</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <p class="eyebrow">Almac&#233;n &#183; Carton box %(ext)s cm</p>
  <h1>C&#243;mo llenar<br>cada carton box</h1>
  <p class="lede">Elige abajo la referencia que est&#225;s empaquetando y sigue los pasos en orden.</p>
  <ul class="rules">
    <li><b>Una sola referencia por carton box.</b> No mezclar modelos.</li>
    <li><b>Sigue los pasos en el orden numerado.</b> Cada piso apoya sobre el anterior; si te lo saltas, no cuadra.</li>
    <li><b>F&#237;jate en la posici&#243;n de la caja en cada paso.</b> En unos pasos va plana, en otros de canto o de pie: es lo que hace que quepan todas.</li>
    <li><b>Cuenta al final.</b> Cada referencia tiene un n&#250;mero exacto de cajas por box.</li>
  </ul>
</header>

<nav class="tabs" role="tablist" aria-label="Referencias">%(tabs)s</nav>

<section id="resumen" role="tabpanel" aria-labelledby="tab-resumen">
  <div class="tablewrap">
    <table>
      <caption>Cu&#225;ntas cajas van en cada carton box</caption>
      <thead><tr><th scope="col">Ref</th><th scope="col">Medidas de la caja (cm)</th>
        <th scope="col">Cajas por box</th><th scope="col">Pasos</th>
        <th scope="col">Box a llenar</th></tr></thead>
      <tbody>%(filas)s</tbody>
    </table>
  </div>
  <p class="note">&#171;Box a llenar&#187; es la previsi&#243;n total de la campa&#241;a: %(tq)s cajas en %(tbx)s
  carton box. El &#250;ltimo box de cada referencia queda incompleto.</p>
  <p class="note">Si una referencia no admite ir de canto o de pie (producto que solo puede viajar tumbado), avisa
  antes de empezar: ese plan hay que recalcularlo y caben menos cajas.</p>
</section>

%(decision)s
%(fichas)s
<footer>Plan de cubicaje calculado sobre medidas interiores de %(util)s cm (%(ext)s exteriores menos
%(merma)s cm de cart&#243;n por cara). Generado con cubicaje.py. Para imprimir: Ctrl+P (sale una referencia por p&#225;gina).</footer>
</div>
<script>
%(js)s
</script>
</body>
</html>
""" % {"css": css, "tabs": tabs, "filas": filas, "tq": miles(tq), "tbx": miles(tbx),
       "decision": seccion_decision(), "fichas": "\n".join(fichas), "js": TABS_JS,
       "ext": "%s &#215; %s &#215; %s" % (cm(CARTON_BOX_EXT[0]), cm(CARTON_BOX_EXT[1]), cm(CARTON_BOX_EXT[2])),
       "util": "%s &#215; %s &#215; %s" % (cm(CL), cm(CW), cm(CH)),
       "merma": cm(MERMA_POR_CARA)}

    aqui = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(aqui, "index.html"), "w", encoding="utf-8") as f:
        f.write(doc)
    with open(os.path.join(aqui, "datos.json"), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    print("\n  Espacio util: %d x %d x %d mm" % (CL, CW, CH))
    print("  Total: %s cajas en %s carton box" % (miles(tq), miles(tbx)))
    print("  Escritos index.html (%s bytes) y datos.json" % miles(len(doc)))

if __name__ == "__main__":
    print("Calculando y verificando planes de carga...")
    generar()
