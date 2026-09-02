# Project
Laboratorio estructural digital 3D del edificio de Ingeniería (UAndes), grupo 4.
Modelo global lineal elástico 3D. Las losas NO se modelan con elementos finitos.
Carga gravitacional de piso = peso propio de losa + terminaciones uniformes (q_G).
Las cargas de losa se transfieren a vigas mediante áreas tributarias explícitas.
El análisis de capacidad RC (fibras, M-phi, P-M) es separado del modelo global.

# Units
Unidades SI: longitud m, fuerza kN, presión kPa, densidad kN/m^3.
Convención: eje de elevación Z. Un solo sistema de unidades en todo el repositorio.

# Structural model
- Elementos: vigas y columnas como elementos lineales viga-columna; muros como
  elementos lineales equivalentes; diafragmas rígidos; apoyos idealizados.
- Casos de carga base independientes: G (gravedad), Q (viva), EX, EY (laterales).
- Q usa la misma geometría tributaria que G, con intensidad diferente.
- Verificaciones obligatorias: carga total por piso, suma de áreas tributarias,
  conservación de carga, equilibrio global, compatibilidad del diafragma.

# Architecture
- OpenSees es dueño del análisis estructural.
- Unity es dueño de visualización, preprocesamiento e interacción.
- JSON (data/model_data.json) es el contrato entre ambos.
- El móvil no ejecuta OpenSees en el proyecto base.

# Data contract
- El esquema vive en python_parser/schema.py.
- El modelo es data/model_data.json; regenerar con python_parser/assemble_model.py (real)
  o python_parser/generate_stub_model.py (stub de pruebas).
- No modificar el contrato JSON sin actualizar schema.py y los tests.

# Verification rules
- Check equilibrium.
- Check units.
- Check local axes.
- Check superposition.
- Never modify benchmark results without justification.
- Rules de verificación se ejecutan así:
    python python_parser/verifications.py data/model_data.json
    python -m pytest python_parser/tests -q

# Cad pipeline
- Los DWG se convierten a DXF con ODA File Converter (python_parser/convert_dwg_to_dxf.py).
- Solo se versionan los planos clave listados en .gitignore.

# Unity
- Versión fijada: Unity 6 (6000.5.10f1), registrada en README.md y
  unity/ProjectSettings/ProjectVersion.txt. No cambiar de versión en mitad del proyecto.
- Proyecto del viewer en unity/ (Assets/, Packages/, ProjectSettings/).
- Única conversión de coordenadas: CoordinateMap (OS (x,y,z) -> Unity (x,z,y)); todas las
  coordenadas deben pasar por ella.
- El viewer lee el snapshot unity/Assets/Data/model_data.json (TextAsset) vía ModelBuilder;
  refrescar con copy_data_to_unity.ps1. La escena Unity NO es fuente de verdad.

# Workflow
- Plan -> Build -> Test -> Review -> Merge.
- Cada cambio importante: objetivo, restricciones, criterio de aceptación, prueba, revisión.
- Cualquier integrante puede ser consultado sobre GDL, ejes locales, rigidez, apoyos,
  diafragmas, áreas tributarias, equilibrio, superposición, diagramas, Fiber Sections,
  curvas P-M y correspondencia OpenSees-Unity.