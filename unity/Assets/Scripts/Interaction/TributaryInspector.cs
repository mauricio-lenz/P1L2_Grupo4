using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Tributary Area Inspector: con Ctrl+click sobre un elemento estructural se
/// listan las áreas tributarias que descargan sobre él y los kN de losa que
/// llegan (caso G y Q). La carga por área se toma de la losa que define cada TA y
/// de su intensidad qG/qQ; los kN = Σ(area_tributaria * q_losa).
/// </summary>
public class TributaryInspector : MonoBehaviour
{
    [SerializeField] private ModelBuilder modelBuilder;

    private string selection = "";
    private string text = "";

    private void Awake()
    {
        if (modelBuilder == null) modelBuilder = GetComponent<ModelBuilder>();
    }

    private void Update()
    {
        if (Input.GetMouseButtonDown(0) && (Input.GetKey(KeyCode.LeftControl) || Input.GetKey(KeyCode.RightControl)))
        {
            Inspect();
        }
    }

    private void Inspect()
    {
        Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);
        RaycastHit hit;
        if (!Physics.Raycast(ray, out hit, 2000f)) { return; }
        var view = hit.collider.GetComponentInParent<ElementView>();
        if (view == null) { selection = "(no es un elemento)"; text = ""; return; }

        int tag = view.ElementTag;
        string kind = view.Kind;
        List<TributaryArea> tas = modelBuilder.TributaryAreas.FindAll(t => t.element == tag);
        var slabQ = new Dictionary<string, Vector2>();
        foreach (var s in modelBuilder.SlabQ)
        {
            slabQ[s.Key] = s.Value;
        }

        double aG = 0, aQ = 0, fG = 0, fQ = 0;
        foreach (var t in tas)
        {
            double qG = slabQ.TryGetValue(t.slab, out Vector2 q) ? q.x : 0;
            double qQ = slabQ.TryGetValue(t.slab, out Vector2 q2) ? q2.y : 0;
            aG += t.area; aQ += t.area;
            fG += t.area * qG;
            fQ += t.area * qQ;
        }

        selection = $"{kind} tag={tag}  [{view.NodeI}|{view.NodeJ}]";
        text = "";
        if (tas.Count == 0)
        {
            text = "Sin areas tributarias asignadas";
            return;
        }
        text += $"Areas tributarias: {tas.Count}\n";
        text += $"Area total: {aG:F3} m2 (G) / {aQ:F3} m2 (Q)\n";
        text += $"Carga de losa (G): {fG:F3} kN\n";
        text += $"Carga de losa (Q): {fQ:F3} kN\n";
        text += modelBuilder.LabelFor(tag);
    }

    private void OnGUI()
    {
        if (selection.Length == 0) return;
        GUIStyle box = new GUIStyle(GUI.skin.box);
        box.normal.background = MakeTex(2, 2, new Color(0.05f, 0.06f, 0.10f, 0.8f));
        GUILayout.BeginArea(new Rect(Screen.width - 340, 12, 320, 150), box);
        GUILayout.Label("INSPECTOR / AREA TRIBUTARIA");
        GUILayout.Label(selection);
        if (text.Length > 0) GUILayout.Label(text);
        GUILayout.EndArea();
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
