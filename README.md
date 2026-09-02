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
| `WASD` / `Q` / `E` | Navegar (Q/E bajar/subes, Shift = rápido) |
| `T` | Alternar nodos |
| `B` | Alternar vigas |
| `C` | Alternar columnas |
| `W` | Alternar muros |
| `S` | Alternar apoyos |
| `D` | Alternar diafragmas (losas) |
| `I` | Mostrar/ocultar IDs de elementos |
| `L` | Mostrar/ocultar ejes locales (flechas magenta) |
| `Ctrl` + clic | **Tributary Area Inspector**: muestra las áreas tributarias de la viga, su área total y los kN de losa que recibe (casos G y Q) |

Implementación: `Assets/Scripts/Interaction/ViewControls.cs` (toggles/IDs/ejes locales) y
`Assets/Scripts/Interaction/TributaryInspector.cs` (inspección). La escena se regenera en modo
batch con `SceneWizard.BuildMain` (`Assets/Editor/SceneWizard.cs`).

- Tests EditMode de `CoordinateMap`: Window > General > Test Runner.

## Demo sugerida (evalua en vivo)
1. Abrir `Assets/Scenes/Main.unity` → Play: se ve el edificio completo (columnas azules, vigas
   amarillas, muros violetas, losas translúcidas a su cota, apoyos rojos).
2. Probar toggles `B/C/W/S/T/D` para aislar un tipo de elemento.
3. `I` para ver los `elementTag` de cada barra; `L` para su eje local.
4. `Ctrl+clic` en una viga del plano → leer en el Inspector su área tributaria y los kN de losa Q/G.
5. Verificaciones (desde la raíz):
   ```
   python python_parser/verifications.py --summary data/model_data.json
   python -m pytest python_parser/tests -q
   ```
