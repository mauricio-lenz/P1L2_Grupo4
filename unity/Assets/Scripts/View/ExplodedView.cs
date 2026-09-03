using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Vista axonométrica explotada del edificio (maqueta estructural técnica).
///
/// - Cámara ortográfica con 3 presets de ángulo (teclas 1/2/3 en ViewControls):
///     1) Isométrica frontal-derecha (elev 35°, azimut 45°) — vista general
///     2) Perfil lateral baja    (elev 10°, azimut  0°) — separación vertical de pisos
///     3) Cenital opuesta        (elev 70°, azimut 225°) — se ven las plantas desde arriba
/// - Cada piso se desplaza verticalmente (UNICAMENTE en Y) según su índice de
///   nivel:  Y = Y_original + floorIndex * explodedOffset * amount.
///   La geometría en planta (X, Z) nunca cambia.
/// - SetExplodedView(bool) / SetExplodedView(float) con transición suave.
/// - SetCameraPreset(int) aplica un preset y re-encuadra.
///
/// No modifica la geometría estructural: solo desplaza la posición visual de los
/// GameObjects ya construidos por ModelBuilder.
/// </summary>
[DefaultExecutionOrder(200)]
public class ExplodedView : MonoBehaviour
{
    [Header("Vista explotada")]
    [Tooltip("Separación vertical (m) entre pisos consecutivos cuando amount=1.")]
    [SerializeField] private float explodedOffset = 1.5f;

    [Tooltip("0 = ensamblado, 1 = totalmente explotado.")]
    [Range(0f, 1f)] [SerializeField] private float amount = 1f;

    [Header("Cámara axonométrica")]
    [Tooltip("Activa la cámara ortográfica axonométrica y el encuadre automático.")]
    [SerializeField] private bool manageCamera = true;

    [Tooltip("Margen relativo alrededor del modelo en el encuadre.")]
    [SerializeField] private float frameMargin = 1.2f;

    [Tooltip("Ángulo de elevación (grados) de la cámara.")]
    [SerializeField] private float cameraElevation = 35f;

    [Tooltip("Ángulo de giro horizontal (res ) de la cámara.")]
    [SerializeField] private float cameraAzimuth = 45f;

    // --- presets de cámara ---------------------------------------------------
    private struct CamPreset
    {
        public readonly string Name;
        public readonly float Elevation;
        public readonly float Azimuth;
        public CamPreset(string name, float elevation, float azimuth)
        { Name = name; Elevation = elevation; Azimuth = azimuth; }
    }

    private static readonly CamPreset[] Presets = new CamPreset[]
    {
        new CamPreset("Isométrica frontal-derecha", 35f,  45f),
        new CamPreset("Perfil lateral baja",        10f,   0f),
        new CamPreset("Cenital opuesta",            70f, 225f),
    };

    private int currentPreset = 0;

    /// <summary>Nombre del preset activo (para la leyenda GUI).</summary>
    public string CurrentPresetName => Presets[currentPreset].Name;

    /// <summary>Índice del preset activo (0..2).</summary>
    public int CurrentPresetIndex => currentPreset;

    // --- data de la configuracion original ------------------------------
    [SerializeField] private ModelBuilder modelBuilder;

    private readonly List<GameObject> animated = new List<GameObject>();
    private readonly List<Vector3> basePos = new List<Vector3>();
    private readonly List<float> floorIdx = new List<float>();

    private Dictionary<string, int> levelIndex;
    private Bounds assembledBounds;
    private bool needsFrame = true;
    private float lastAmount = float.NaN;

    private void Awake()
    {
        if (modelBuilder == null) modelBuilder = GetComponent<ModelBuilder>();
    }

    private void Start()
    {
        if (modelBuilder == null) return;
        BuildLevelIndex();
        RegisterAllObjects();
        ComputeAssembledBounds();
        needsFrame = true;
    }

    private void Update()
    {
        if (animated.Count == 0) return;
        // detectar cambio para re-encuadrar la camara al explotar/ensamblar
        if (Mathf.Abs(amount - lastAmount) > 0.0005f)
        {
            lastAmount = amount;
            needsFrame = true;
        }
        float t = Mathf.SmoothStep(0f, 1f, amount);
        for (int i = 0; i < animated.Count; i++)
        {
            Vector3 p = basePos[i];
            p.y += floorIdx[i] * explodedOffset * t;
            animated[i].transform.position = p;
        }
        if (manageCamera && needsFrame && Camera.main != null)
        {
            FrameCamera();
            needsFrame = false;
        }
    }

    /// <summary>amount 1 si enabled, 0 si no (con transición suave).</summary>
    public void SetExplodedView(bool enabled)
    {
        amount = enabled ? 1f : 0f;
        needsFrame = true;
    }

    /// <summary>Control fino de la separación: 0 = ensamblado, 1 = explotado.</summary>
    public void SetExplodedView(float value)
    {
        amount = Mathf.Clamp01(value);
        needsFrame = true;
    }

    public float CurrentAmount => amount;

    /// <summary>
    /// Aplica un preset de cámara por índice (0, 1, 2) y re-encuadra.
    /// Si idx es inválido, no hace nada.
    /// </summary>
    public void SetCameraPreset(int idx)
    {
        if (idx < 0 || idx >= Presets.Length) return;
        currentPreset = idx;
        cameraElevation = Presets[idx].Elevation;
        cameraAzimuth = Presets[idx].Azimuth;
        needsFrame = true;
    }

    /// <summary>Cicla al siguiente preset (0→1→2→0).</summary>
    public void CycleCameraPreset()
    {
        SetCameraPreset((currentPreset + 1) % Presets.Length);
    }

    private void BuildLevelIndex()
    {
        levelIndex = new Dictionary<string, int>();
        if (modelBuilder.Model.levels == null) return;
        // ordenar por elevacion ascendente: el piso mas bajo tiene indice 0
        var sortedLevels = new List<LevelData>(modelBuilder.Model.levels);
        sortedLevels.Sort((a, b) => a.elevation.CompareTo(b.elevation));
        for (int i = 0; i < sortedLevels.Count; i++)
            levelIndex[sortedLevels[i].id] = i;
    }

    private void RegisterAllObjects()
    {
        if (modelBuilder.Model.elements != null)
        {
            foreach (GameObject go in modelBuilder.ElementObjects)
            {
                var view = go.GetComponent<ElementView>();
                if (view == null) continue;
                Register(go, FloorOfElement(view.ElementTag));
            }
        }

        if (modelBuilder.Model.slabs != null)
        {
            foreach (GameObject go in modelBuilder.SlabObjects)
            {
                // la base solida (cajon) se queda abajo (indice 0)
                if (go.name.StartsWith("BasementBox")) { Register(go, 0f); continue; }
                string slabLevel = SlabLevelFor(go.name);
                Register(go, LevelOf(slabLevel));
            }
        }

        if (modelBuilder.NodeObjects != null)
        {
            // los nodos suben con su propio nivel para no quedar cruzados
            foreach (GameObject go in modelBuilder.NodeObjects)
            {
                registerNode(go);
            }
        }

        if (modelBuilder.SupportObjects != null)
        {
            foreach (GameObject go in modelBuilder.SupportObjects)
            {
                // los apoyos quedan en el nivel mas bajo (base, indice 0)
                Register(go, 0f);
            }
        }
    }

    // nodos: usar el nivel del nodo guardado por ModelBuilder no esta disponible por
    // indice de objeto; usamos el nivel mas cercano por su posicion Y original.
    private void registerNode(GameObject go)
    {
        int idx = NearestLevel(CoordinateMap.UnityToOs(go.transform.position).z);
        Register(go, idx);
    }

    private int FloorOfElement(int elementTag)
    {
        foreach (ElementData e in modelBuilder.Model.elements)
            if (e.tag == elementTag)
                return LevelOf(e.level);
        return 0;
    }

    private string SlabLevelFor(string goName)
    {
        // nombre: Slab_<id>
        int underscore = goName.IndexOf('_');
        if (underscore < 0) return null;
        string id = goName.Substring(underscore + 1);
        if (modelBuilder.Model.slabs != null)
            foreach (SlabData s in modelBuilder.Model.slabs)
                if (s.id == id)
                    return s.level;
        return null;
    }

    private int LevelOf(string levelId)
    {
        if (levelId != null && levelIndex != null && levelIndex.ContainsKey(levelId))
            return levelIndex[levelId];
        return 0;
    }

    private int NearestLevel(float osZ)
    {
        if (levelIndex == null) return 0;
        int best = 0; float bestD = float.PositiveInfinity;
        foreach (KeyValuePair<string, int> kv in levelIndex)
        {
            float e = modelBuilder.LevelElevations.ContainsKey(kv.Key)
                ? modelBuilder.LevelElevations[kv.Key] : 0f;
            float d = Mathf.Abs(e - osZ);
            if (d < bestD) { bestD = d; best = kv.Value; }
        }
        return best;
    }

    private void Register(GameObject go, float idx)
    {
        animated.Add(go);
        basePos.Add(go.transform.position);
        floorIdx.Add(idx);
    }

    private void ComputeAssembledBounds()
    {
        var b = new Bounds();
        bool any = false;
        foreach (Vector3 baseP in basePos)
        {
            if (!any) { b = new Bounds(baseP, Vector3.zero); any = true; }
            else b.Encapsulate(baseP);
        }
        // incluir la altura explotada maxima (mayor indice de piso)
        float maxIdx = 0f;
        foreach (float f in floorIdx) if (f > maxIdx) maxIdx = f;
        Vector3 top = b.max;
        top.y += maxIdx * explodedOffset;
        b.Encapsulate(top);
        assembledBounds = b;
    }

    private void FrameCamera()
    {
        Camera cam = Camera.main;
        Bounds b = assembledBounds;
        Vector3 center = b.center;
        float radius = (b.max - b.min).magnitude * 0.5f;

        // direccion de la camara segun elevacion/azimut (X derecha, Z adelante en el plano)
        float e = cameraElevation * Mathf.Deg2Rad;
        float a = cameraAzimuth * Mathf.Deg2Rad;
        Vector3 dir = new Vector3(Mathf.Cos(e) * Mathf.Sin(a),
                                  Mathf.Sin(e),
                                  Mathf.Cos(e) * Mathf.Cos(a));
        dir.Normalize();

        cam.orthographic = true;
        cam.transform.position = center + dir * (radius * 2.5f);
        cam.transform.LookAt(center, Vector3.up);

        float visibleSize = (radius * frameMargin);
        if (Camera.main.orthographic)
            cam.orthographicSize = visibleSize;
    }
}
