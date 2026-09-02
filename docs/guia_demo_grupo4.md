# Guía de Demostración — Lab Semana 2 (Grupo 4)

Instrucciones de la demo en vivo y respuestas modelo a las preguntas del profesor.
La demo se hace contra el commit `8849849` (`master`), repo público `P1L2_Grupo4`.

---

## 1. Orden de la demo (5–7 min)

1. **Verificaciones (línea de comandos, en la raíz del repo):**
   ```
   python python_parser/verifications.py --summary data/model_data.json
   python -m pytest python_parser/tests -q
   ```
   Explicar: `RESULTADO GLOBAL: OK` = pasan los 5 checks; 9 tests Python + 4 tests Unity en verde.

2. **Visual (Unity):** abrir `unity/` en Hub → `Assets/Scenes/Main.unity` → **Play**.
   - Se ve el edificio completo: columnas azules, vigas amarillas, muros violetas, losas translúcidas a su cota, apoyos rojos.
   - Navegar con `WASD` (Shift = rápido) y orbitar con clic derecho + mover el mouse.

3. **Toggles** (`B/C/W/S/T/D`) — aislar un tipo de elemento para mostrar que el modelo distingue cada uno.

4. **IDs y eje local** (`I` y `L`) — mostrar `elementTag` y la flecha magenta del eje local de una viga.

5. **Tributary Area Inspector** (`Ctrl` + clic sobre una viga) — leer el área tributaria y los kN que recibe.

---

## 2. Ejemplo concreto para la demo

**Viga de P1, elementTag = 1153** (la de mayor carga del piso):

| Dato | Valor |
|------|-------|
| kind | `beam` |
| sección | `V30x50` (losa P1: 0.30×0.50 m, hormigón C25) |
| nodos | `i=1029010` → `j=1032010` |
| eje local | `(1.0, 0.0, 0.0)` en OS → eX |
| áreas tributarias | **76** |
| área tributaria total | **203.73 m²** |
| kN de losa (G) | **1268.65 kN** (= 203.73 × 6.227) |
| kN de losa (Q) | **599.38 kN** (= 203.73 × 2.942) |
| apoyo en extremo | ninguno directo (viga → columnas → apoyos N0) |

Con esto se responde "¿qué área tributaria carga esta viga?" y "¿cuántos kN llegan?" con números exactos.

---

## 3. Respuestas modelo a preguntas típicas

### "¿Qué elementTag tiene este elemento?"
Con `I` activado aparecen los tags numerados junto a cada barra. Para el 1153: viga de P1, sección V30x50, entre nodos 1029010 y 1032010.

### "¿Qué apoyos tiene?"
Los apoyos son los 22 nodos de la base (nivel N0, z=0). En el contrato `supports[]` restringen traslaciones (`ux, uy, uz = true`) y dejan libres los giros (`rx, ry, rz = false`) — apoyos **pivotantes** (articulación esférica). Se ven como cubos rojos bajo el edificio.

### "¿Cuál es su eje local?"
El eje local X de cada elemento viene en el contrato (`local_x`). Para el 1153 es `(1,0,0)` = eje X del plano. Con `L` se ve la flecha magenta. La conversión a coordenadas es la única de `CoordinateMap` (OS `(x,y,z)` → Unity `(x,z,y)`).

### "¿Qué área tributaria carga esta viga? / ¿cuántos kN llegan?"
`Ctrl`+clic sobre la viga 1153 → Inspector: **76 áreas tributarias, 203.73 m², G=1268.65 kN, Q=599.38 kN**.
Mecánica: la losa se particiona en áreas tributarias; cada TA se asigna a la viga (element) más cercana; los kN = Σ(area_TA × q_losa). Esto lo garantiza el check `conservacion_carga` (Σ TA × q = q × área de losa).

---

## 4. Explicación de los checks (si pregunta "¿por qué pasan?")

- **carga_total_por_piso**: q × área de cada losa → total por nivel (P1 G=21098.9 kN, P2=17611.0, P3=6325.7).
- **suma_areas_tributarias**: Σ de las 6624 TA por piso = área de su losa (sin huecos ni traslapes).
- **conservacion_carga**: lo transferido a vigas (Σ TA × q) = lo que la losa recibe (q × área).
- **equilibrio_global**: cargas aplicadas (G 45035.5 kN, Q 21277.4) = reacciones en los 22 apoyos.
- **compatibilidad_diafragma**: todos los nodos de cada piso (P1:95, P2:67, P3:31) están en su diafragma, coplanares y a la cota del nivel.

`RESULTADO GLOBAL: OK` = las cinco se cumplen.

---

## 5. Pipeline (si pregunta "¿cómo se construyó?")

DWG → DXF (ODA) → `python_parser/parse_dxf.py` (lee retícula, columnas, vigas, muros, espesores de losa) → `assemble_model.py` (genera nodos, elementos, secciones, materiales, apoyos, diafragmas, áreas tributarias, casos G/Q con q de `2017_67-700`) → `data/model_data.json` → copia a `unity/Assets/Data/` (viewer).

La losa **no** se modela con elementos finitos: la carga va a las vigas por áreas tributarias explícitas (convención del lab).

---

## 6. Si el profesor insiste en algo fuera de esto
- **Cargas especiales** (SC=800, PM.ADIC.=2800, equipos puntuales 6700–13000 kg): están identificadas en `docs/planos_analysis.md` (notas) pero **no** incluidas en el modelo base; declarar que el modelo actual usa sobrecarga uniforme representativa y que las puntuales/zonas especiales son trabajo posterior si preguntan por un valor puntual exacto.
- **N.O.G. por piso**: el modelo usa 3.5 m por piso (N0=0, P1=3.5, P2=7.0, P3=10.5). Confirmar contra el plano si preguntan por altura exacta de un nivel.
