# P1L2 - Edificio de Ingeniería (UAndes) · Grupo 4

Modelo estructural digital 3D del edificio de Ingeniería: OpenSees (análisis) + Unity
(visualización/QA), unidos por el contrato `data/model_data.json`.

## Estado
- Pipeline DWG → DXF (ODA) → `python_parser/parse_dxf.py` → `assemble_model.py` → modelo real.
- `data/model_data.json`: 3 pisos (P1/P2/P3) del proyecto 2017_67, unidades SI (m, kN, kPa),
  eje Z vertical. Cargas reales de la hoja `2017_67-700` (q_G ≈ 6.23 kPa, q_Q ≈ 2.94 kPa).
- Verificaciones obligatorias (5 checks) + 9 tests: verdes.
  ```
  python python_parser/verifications.py data/model_data.json
  python -m pytest python_parser/tests -q
  ```

## Unity
- **Versión fijada:** Unity 6 (`6000.5.10f1`, ver `unity/ProjectSettings/ProjectVersion.txt`).
  No actualizar de versión durante el proyecto.
- Proyecto en `unity/` (Assets + Packages + ProjectSettings). Escena principal `Assets/Scenes/Main.unity`.
- Única conversión de coordenadas: `CoordinateMap` (`OS (x,y,z) → Unity (x,z,y)`).
- Viewer: `ModelBuilder` (lee el TextAsset `Assets/Data/model_data.json` → nodos, elementos
  centrelines, losas, apoyos). El snapshot se refresca con `copy_data_to_unity.ps1`.
  Navegación: `FreeFlyCamera` (WASD, clic derecho).

### Controles del viewer (en Play)
| Tecla | Acción |
|-------|--------|
| `WASD` / `Q` / `E` | Navegar (Q/E bajar/subir, Shift = rápido) |
| `X` | Alternar **vista explotada** (separar pisos en vertical, axonométrica) |
| `T` | Alternar nodos |
| `B` | Alternar vigas |
| `C` | Alternar columnas |
| `W` | Alternar muros |
| `S` | Alternar apoyos |
| `D` | Alternar diafragmas (losas) |
| `I` | Mostrar/ocultar IDs de elementos |
| `L` | Mostrar/ocultar ejes locales (flechas magenta) |
| `Ctrl` + clic | **Tributary Area Inspector**: muestra las áreas tributarias de la viga, su área total y los kN de losa que recibe (casos G y Q) |

### Vista explotada (maqueta estructural técnica)
`Assets/Scripts/View/ExplodedView.cs` convierte la visualización en una **vista axonométrica
explotada**: cámara ortográfica en ángulo isométrico (fachada + lateral) y cada piso separado
verticalmente con un desplazamiento `floorIndex * explodedOffset * amount` (solo en Y; X/Z sin
cambios). Los colores son planos y legibles: **losas verde claro, vigas azul, pilares rojo**,
base sólida de subterráneos marrón, fondo neutro.

Controles desde el Inspector (componente `ExplodedView` en el GameObject `App`):
- `explodedOffset`: separación (m) entre pisos consecutivos (por defecto `1.5`).
- `amount`: 0 = ensamblado, 1 = totalmente explotado (deslizador).
- `manageCamera`: activa el encuadre automático axonométrico.

API: `SetExplodedView(bool)` y `SetExplodedView(float amount)` con transición suave
(`SmoothStep`); al volver a `amount = 0` todo regresa a su posición estructural original sin
reconstruir el modelo. Tecla `X` lo alterna en vivo.

Implementación: `Assets/Scripts/Interaction/ViewControls.cs` (toggles/IDs/ejes locales) y
`Assets/Scripts/Interaction/TributaryInspector.cs` (inspección). La escena se regenera en modo
batch con `SceneWizard.BuildMain` (`Assets/Editor/SceneWizard.cs`).

- Tests EditMode de `CoordinateMap`: Window > General > Test Runner.

## Demo sugerida (evalua en vivo)
Guía completa con respuestas modelo: **`docs/guia_demo_grupo4.md`**.
1. Abrir `Assets/Scenes/Main.unity` → Play: se ve el edificio en **vista explotada**
   axonométrica (losas verde claro, vigas azules, pilares rojos, base de subterráneos marrón),
   con los **voladizos de losa** de los pisos superiores (P2/P3 y azotea sobresalen en el
   lateral y el fondo).
2. `X` para alternar entre vista ensamblada y explotada.
3. Probar toggles `B/C/W/S/T/D` para aislar un tipo de elemento.
4. `I` para ver los `elementTag` de cada barra; `L` para su eje local.
4. `Ctrl+clic` en una viga del plano → leer en el Inspector su área tributaria y los kN de losa Q/G.
5. Verificaciones (desde la raíz):
   ```
   python python_parser/verifications.py --summary data/model_data.json
   python -m pytest python_parser/tests -q
   ```
