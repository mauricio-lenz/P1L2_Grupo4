# Análisis de planos DXF — hallazgos y decisiones (Grupo 4)

## Unidades del dibujo: CM (0.01 m) — verificado
- Los valores geométricos (columnas `P. 70x70` = 70 u, vigas `V. 60/80` = caras a 60 u,
  muros `M.H.A. e=30` = 30 u, `LOSA e=15` = 15 u, `DILATACION 10 CM`, `CONTRAFLECHA (cm.)`)
  solo son físicamente coherentes en **centímetros**.
- Retícula de ejes: separaciones 2.75 m / 5.0 m (imposible en mm, absurda en dm).
- Por lo tanto: **SCALE_CM_TO_M = 0.01** · coordenada_dibujo → metros.
- La escala anotada (1:75, 1:150) es escala de PLOTEO, no del modelo (el modelo es 1:1).

## Láminas con estructura (catálogo)
| Lámina | Contenido | Niveles (texto RLE-NIVELES) |
|---|---|---|
| 2017_67-100 | Fundaciones/pilotes `P.` | N.R. -4.01, -7.97, VAR |
| 2017_67-101 | Planta estructural piso 1 | N.O.G. -0.95, -1.54, -1.90, -4.21; N.R. -0.05; LOSA e=15 |
| 2017_67-102 | Planta estructural piso 2 (más pilares: 196 líneas) | — |
| 2017_67-103 | Planta estructural piso 3 | — |
| 2017_67-201/202/203/204/205 | Plantas de losas (sin ejes) | — |
| 2017_67-700 | Planta de cargas (HATCH CARGAS, escala 1:150) | — |
| 2024_22-100 | Continuación subterráneo | N.R. -8.12, -8.185, N.O.G. -9.37 |
| 2024_22-101 | Continuación planta | N.O.G. -5.945 |
| 2024_22-102 | Continuación planta piso alto | — |

Nota: 2017 y 2024 tienen ORIGENES (datum) distintos (X0≈0 vs X0≈270 u). No se
empalman sin transformación. Ver archivo_inventory.txt para catálogo completo.

## Capas estructurales (nomenclatura)
- `RLE-EJE`: burbujas de ejes (MTEXT + CIRCLE, códigos de eje).
- `RLE-EJES`: líneas de retícula (verticales: x cte; horizontales: y cte).
- `RLE-PILAR`: rectángulos de columnas (4 LINES por pilar → agrupar para obtener centro+dim).
- `RLE-VIGA`: pares de líneas paralelas = caras de vigas (centroide = eje de la viga).
- `RLE-MURO`: pares de líneas de muros (espesor = separación de caras).
- `RLE-LOSA` / `RLA-LOSAS`: bordes/etiquetas de losas.
- `RLE-NIVELES`: cotas de niveles (N.O.G., N.R.).
- `RLE-TEXTO-1`: tags de sección (`V. {w}/{h}`, `P. {b}x{h}`, `M.H.A. e={t}`).
- `HATCH CARGAS` (en -700): planta de cargas con hatch por paño.
- `RLA-COTAS` / `RLA-COTAS1`: dimensiones.

## Decisiones de modelado
- Losas NO se modelan con FE; se transfieren por áreas tributarias (triángulo por paño,
  igual geometría para G y Q) — regla ya codificada y verificada en la fase 1.
- **NO hay voladizos**: las losas no sobresalen de la retícula de columnas. Una medición
  previa contra `RLE-LOSA` sugirió voladizos en P2/P3 y azotea, pero al rectificar contra
  los planos resultaron **inexistentes**; se retiró la tabla `CANTILEVER` por completo.
- Vigas implícitas de marco: solo se conectan nodos del MISMO nivel que comparten una
  línea recta exacta (misma X o misma Y) y que son consecutivos (sin nodo intermedio),
  y únicamente si no hay viga/muro por evidencia. La agrupación es por coordenada real,
  no por índice de tag, con lo que **nunca se generan diagonales** ni tramos cruzados
  (bug corregido). Completa la grilla de pórticos donde la evidencia escrita es escasa
  (p. ej. -102). Verificado: 0 diagonales en el modelo.
- q_G real proviene de la hoja de cargas (2017_67-700) + ETG; pendiente de extraer valores.
- Los niveles/secciones reales se asignan por lámina; verificación diaria con
  `python python_parser/verifications.py data/model_data.json`.

## Hoja de cargas 2017_67-700 ("PLANTA CIELO", escala 1:150)
Rótulos en capa `HATCH CARGAS`, en **kg/m<sup>2</sup>** (si el rótulo dice solo "Kg" sin "/m"
es carga **puntual** de equipo). Fórmula de rotulación:
`PP. LOSA = e(m)x2500 Kg/m2` (γ=2500 kg/m³ ≈ 24.5 kN/m³), `PM. ADIC. = ...  Kg/m2`,
`SC = ... Kg/m2`.

Valores por zona observados:
| Concepto | Típico | Especiales |
|---|---|---|
| SC (carga viva) | 300 | 200, 250, 400, 500; **800** (4.º piso); puntuales 6700/6000/7000 kg |
| PM. ADIC. (terminaciones) | 260 | 200, 300, 350; **2800** (zona pesada); puntuales 10000/13000 kg |

Valores codificados en el modelo (P1/P2/P3, conservador):
- q_G = 0.15×2500 + 260 = 375 + 260 = 635 kg/m² ≈ **6.23 kPa**
- q_Q = SC 300 kg/m² ≈ **2.94 kPa**
- Conversión usada: ×9.80665/1000.

Cargas puntuales de equipo y zonas pesadas (4.º piso/azotea, parking) NO entran aún en el
modelo global de 3 pisos (P1–P3); quedan en `notes_todo` del contrato.

## Pipeline
1. Inventario: `python python_parser/inventory_dxf.py cad_files/dxf`
2. Inspección fina: `python python_parser/inspect_plan.py <dxf> [--layers ...]`
3. Parser: `python python_parser/parse_dxf.py` (en desarrollo).