using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Controles en vivo del viewer (Leyenda + teclas):
///   T       -> alternar nodos
///   B       -> alternar vigas
///   C       -> alternar columnas
///   W       -> alternar muros
///   S       -> alternar apoyos
///   D       -> alternar diafragmas (losas)
///   I       -> alternar IDs (etiquetas numeradas)
///   L       -> alternar ejes locales
///   Click izq + Ctrl -> inspeccionar elemento (Tributary Area Inspector)
/// Los estados se muestran y se activan/desactivan solo componentes Renderer.
/// </summary>
public class ViewControls : MonoBehaviour
{
    [SerializeField] private ModelBuilder modelBuilder;
    [SerializeField] private GUISkin skin;

    public bool ShowIds { get; private set; }
    public bool ShowLocalAxes { get; private set; }

    // Estado de visibilidad por tipo.
    private bool nodesOn = true;
    private bool beamsOn = true;
    private bool columnsOn = true;
    private bool wallsOn = true;
    private bool supportsOn = true;
    private bool slabsOn = true;
    private bool baseOn = true;

    private readonly Dictionary<int, Vector3> elementCenters = new Dictionary<int, Vector3>();
    private readonly Dictionary<int, string> elementKind = new Dictionary<int, string>();
    private readonly Dictionary<int, Vector3> elementAxis = new Dictionary<int, Vector3>();

    private GameObject elementArrowCube;
    private GameObject elementArrowCone;

    private void Awake()
    {
        if (modelBuilder == null) modelBuilder = GetComponent<ModelBuilder>();
    }

    private void Start()
    {
        PreloadElementData();
        BuildArrowParts();
        // Las "paredes" (muros) se dejan apagadas por defecto para que no saturen
        // la vista; se activan con la tecla W (y sus apoyos asociados van con ellas).
        FilterElements("wall", false);
        SetGroup(modelBuilder.SupportWallObjects, false);
        wallsOn = false;
    }

    private void PreloadElementData()
    {
        foreach (GameObject go in modelBuilder.ElementObjects)
        {
            var view = go.GetComponent<ElementView>();
            if (view == null) continue;
            Vector3 a = modelBuilder.NodePos(view.NodeI);
            Vector3 b = modelBuilder.NodePos(view.NodeJ);
            elementCenters[view.ElementTag] = 0.5f * (a + b);
            elementKind[view.ElementTag] = view.Kind;
            elementAxis[view.ElementTag] = view.LocalX.sqrMagnitude > 0.0001f
                ? view.LocalX : (b - a).normalized;
        }
    }

    private void BuildArrowParts()
    {
        elementArrowCube = GameObject.CreatePrimitive(PrimitiveType.Cube);
        elementArrowCube.name = "ElemLocalArrowShaft";
        elementArrowCube.GetComponent<Renderer>().material.color = Color.magenta;
        elementArrowCube.SetActive(false);

        elementArrowCone = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        elementArrowCone.name = "ElemLocalArrowHead";
        elementArrowCone.GetComponent<Renderer>().material.color = Color.magenta;
        elementArrowCone.SetActive(false);
    }

    private void Update()
    {
        if (elementCenters.Count == 0 && modelBuilder.ElementObjects.Count > 0)
        {
            PreloadElementData();
        }
        if (Input.GetKeyDown(KeyCode.T)) { nodesOn = !nodesOn; SetGroup(modelBuilder.NodeObjects, nodesOn); }
        if (Input.GetKeyDown(KeyCode.S)) { supportsOn = !supportsOn; SetGroup(modelBuilder.SupportObjects, supportsOn); }
        if (Input.GetKeyDown(KeyCode.D)) { slabsOn = !slabsOn; SetGroup(modelBuilder.SlabObjects, slabsOn); }
        if (Input.GetKeyDown(KeyCode.G)) { baseOn = !baseOn; SetGroup(modelBuilder.BasementObjects, baseOn); }
        if (Input.GetKeyDown(KeyCode.B)) { beamsOn = !beamsOn; FilterElements("beam", beamsOn); }
        if (Input.GetKeyDown(KeyCode.C)) { columnsOn = !columnsOn; FilterElements("column", columnsOn); }
        if (Input.GetKeyDown(KeyCode.W))
        {
            wallsOn = !wallsOn;
            FilterElements("wall", wallsOn);
            SetGroup(modelBuilder.SupportWallObjects, wallsOn);
        }
        if (Input.GetKeyDown(KeyCode.I)) { ShowIds = !ShowIds; }
        if (Input.GetKeyDown(KeyCode.L)) { ShowLocalAxes = !ShowLocalAxes; BuildArrowParts(); }
    }

    private void OnGUI()
    {
        GUIStyle box = skin != null ? skin.box : new GUIStyle(GUI.skin.box);
        GUIStyle label = skin != null ? skin.label : new GUIStyle(GUI.skin.label);
        label.alignment = TextAnchor.MiddleLeft;
        box.normal.background = MakeTex(2, 2, new Color(0.05f, 0.06f, 0.10f, 0.75f));

        GUILayout.BeginArea(new Rect(12, 12, 300, 205), box);
        GUILayout.Label("CONTROLES (vivo)", label);
        GUILayout.Label("T  nodos      [ON/OFF]", label);
        GUILayout.Label("B  vigas      [ON/OFF]", label);
        GUILayout.Label("C  columnas   [ON/OFF]", label);
        GUILayout.Label("W  muros      [ON/OFF]", label);
        GUILayout.Label("S  apoyos     [ON/OFF]", label);
        GUILayout.Label("D  diafragmas [ON/OFF]", label);
        GUILayout.Label("G  base solida [ON/OFF]", label);
        GUILayout.Label("I  IDs        [ON/OFF]", label);
        GUILayout.Label("L  ejes locales [ON/OFF]", label);
        GUILayout.Label("Ctrl+Click en un elemento = inspeccionar", label);
        GUILayout.EndArea();

        if (ShowIds)
        {
            GUIStyle idLabel = new GUIStyle(GUI.skin.label) { alignment = TextAnchor.MiddleCenter };
            idLabel.normal.textColor = Color.yellow;
            foreach (GameObject viewGo in modelBuilder.ElementObjects)
            {
                var view = viewGo.GetComponent<ElementView>();
                if (view == null) continue;
                Vector3 scr = Camera.main.WorldToScreenPoint(elementCenters[view.ElementTag]);
                if (scr.z < 0) continue;
                GUI.Label(new Rect(scr.x - 20, Screen.height - scr.y - 10, 40, 20),
                          view.ElementTag.ToString(), idLabel);
            }
        }

        if (ShowLocalAxes)
        {
            for (int i = 0; i < modelBuilder.ElementObjects.Count; i++)
            {
                var view = modelBuilder.ElementObjects[i].GetComponent<ElementView>();
                if (view == null) continue;
                Vector3 center = elementCenters[view.ElementTag];
                Vector3 axis = elementAxis[view.ElementTag];
                DrawAxis(center, axis, 1.5f);
            }
        }
    }

    private void DrawAxis(Vector3 origin, Vector3 dir, float length)
    {
        elementArrowCube.transform.position = origin + dir * (length * 0.5f);
        elementArrowCube.transform.localScale = new Vector3(0.08f, length, 0.08f);
        elementArrowCube.transform.rotation = Quaternion.FromToRotation(Vector3.up, dir);
        elementArrowCube.SetActive(true);
        elementArrowCone.transform.position = origin + dir * length;
        elementArrowCone.transform.localScale = Vector3.one * 0.25f;
        elementArrowCone.transform.rotation = Quaternion.FromToRotation(Vector3.up, dir);
        elementArrowCone.SetActive(true);
    }

    private void FilterElements(string kind, bool on)
    {
        for (int i = 0; i < modelBuilder.ElementObjects.Count; i++)
        {
            var view = modelBuilder.ElementObjects[i].GetComponent<ElementView>();
            if (view != null && view.Kind == kind)
                modelBuilder.ElementObjects[i].SetActive(on);
        }
    }

    private static void SetGroup(List<GameObject> objs, bool on)
    {
        foreach (GameObject o in objs) o.SetActive(on);
    }

    private static Texture2D MakeTex(int w, int h, Color col)
    {
        var txt = new Color[w * h];
        for (int i = 0; i < txt.Length; i++) txt[i] = col;
        var t = new Texture2D(w, h);
        t.SetPixels(txt);
        t.Apply();
        return t;
    }
}
