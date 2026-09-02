using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Procesa el JSON de data/model_data.json (TextAsset) y construye la escena:
/// nodos (esferas), elementos (cilindros por tipo), losas (planos) y apoyos.
/// Toda coordenada pasa por CoordinateMap.OsToUnity.
/// </summary>
public class ModelBuilder : MonoBehaviour
{
    [SerializeField] private TextAsset modelJson;

    private ModelData model;

    private void Start()
    {
        if (modelJson == null)
        {
            Debug.LogError("ModelBuilder: asigna el TextAsset de data/model_data.json");
            return;
        }
        model = ModelDataLoader.Load(modelJson);
        var nodeIndex = ModelDataLoader.BuildNodeIndex(model);
        var elementTags = new System.Collections.Generic.HashSet<int>();

        BuildNodes(nodeIndex);
        BuildElements(nodeIndex, elementTags);
        BuildSlabs();
        BuildSupports(nodeIndex);
        Debug.Log($"ModelBuilder: {model.nodes.Count} nodos, {model.elements.Count} " +
                  $"elementos, {model.slabs.Count} losas, {model.supports.Count} apoyos.");
    }

    private void BuildNodes(Dictionary<int, NodeData> nodeIndex)
    {
        foreach (NodeData n in model.nodes)
        {
            if (n == null) continue;
            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            go.name = $"Node_{n.tag}";
            go.transform.SetParent(transform, false);
            go.transform.position = CoordinateMap.OsToUnity(n.x, n.y, n.z);
            go.transform.localScale = Vector3.one * 0.18f;
            var r = go.GetComponent<Renderer>();
            r.material.color = new Color32(90, 90, 100, 255);
        }
    }

    private void BuildElements(Dictionary<int, NodeData> nodeIndex,
                               System.Collections.Generic.HashSet<int> elementTags)
    {
        foreach (ElementData e in model.elements)
        {
            if (e == null) continue;
            if (elementTags.Contains(e.tag))
            {
                throw new System.Exception($"ElementTag duplicado: {e.tag}");
            }
            elementTags.Add(e.tag);

            if (!nodeIndex.TryGetValue(e.i, out NodeData ni) ||
                !nodeIndex.TryGetValue(e.j, out NodeData nj))
            {
                throw new System.Exception(
                    $"Element {e.tag} referencia nodo inexistente: {e.i} o {e.j}");
            }

            float radius = RadiusFor(e);
            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            go.name = $"Element_{e.tag}";
            go.transform.SetParent(transform, false);
            var view = go.AddComponent<ElementView>();
            view.Initialize(e.tag, e.i, e.j, e.kind, radius);
            Vector3 a = CoordinateMap.OsToUnity(ni.x, ni.y, ni.z);
            Vector3 b = CoordinateMap.OsToUnity(nj.x, nj.y, nj.z);
            view.SetEndpoints(a, b);
            go.GetComponent<Renderer>().material.color = ColorFor(e.kind);
        }
    }

    private void BuildSlabs()
    {
        if (model.slabs == null) return;
        foreach (SlabData s in model.slabs)
        {
            if (s == null || s.polygon == null || s.polygon.Count < 3) continue;
            GameObject go = new GameObject($"Slab_{s.id}");
            go.transform.SetParent(transform, false);
            var mf = go.AddComponent<MeshFilter>();
            var mr = go.AddComponent<MeshRenderer>();
            mf.mesh = SlabMesh(s.polygon);
            mr.material = new Material(Shader.Find("Standard"))
            {
                color = new Color32(150, 165, 190, 90)
            };
        }
    }

    private void BuildSupports(Dictionary<int, NodeData> nodeIndex)
    {
        if (model.supports == null) return;
        foreach (SupportData s in model.supports)
        {
            if (s == null || !nodeIndex.TryGetValue(s.node, out NodeData n)) continue;
            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = $"Support_{s.node}";
            go.transform.SetParent(transform, false);
            go.transform.position = CoordinateMap.OsToUnity(n.x, n.y, n.z) + Vector3.down * 0.1f;
            go.transform.localScale = Vector3.one * 0.35f;
            go.GetComponent<Renderer>().material.color = new Color32(210, 90, 60, 255);
        }
    }

    private static Mesh SlabMesh(System.Collections.Generic.List<System.Collections.Generic.List<float>> poly)
    {
        var verts = new Vector3[poly.Count];
        for (int k = 0; k < poly.Count; k++)
        {
            verts[k] = CoordinateMap.OsToUnity(poly[k][0], poly[k][1], 0f);
        }
        var tris = new int[3 * (poly.Count - 2)];
        int t = 0;
        for (int k = 1; k < poly.Count - 1; k++)
        {
            tris[t++] = 0;
            tris[t++] = k;
            tris[t++] = k + 1;
        }
        var mesh = new Mesh { vertices = verts, triangles = tris };
        mesh.RecalculateNormals();
        return mesh;
    }

    private static float RadiusFor(ElementData e)
    {
        switch (e.kind)
        {
            case "column": return 0.35f;
            case "beam": return 0.16f;
            case "wall": return 0.30f;
            default: return 0.12f;
        }
    }

    private static Color ColorFor(string kind)
    {
        switch (kind)
        {
            case "column": return new Color32(70, 130, 180, 255);
            case "beam": return new Color32(220, 200, 90, 255);
            case "wall": return new Color32(140, 90, 190, 255);
            default: return new Color32(180, 180, 180, 255);
        }
    }
}