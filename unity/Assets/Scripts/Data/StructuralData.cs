using System;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Contrato de datos del modelo (espejo de data/model_data.json, schema 0.1.0).
/// JsonUtility ignora claves extra, así que basta declarar los campos que se consumen.
/// </summary>

[Serializable]
public class NodeData
{
    public int tag;
    public float x;
    public float y;
    public float z;
    public string level;
}

[Serializable]
public class ElementData
{
    public int tag;
    public int i;
    public int j;
    public string kind;
    public string section;
    public string level;
    public List<float> local_x;
}

[Serializable]
public class TributaryArea
{
    public string id;
    public int element;
    public string slab;
    public string level;
    public string @case;
    public float area;
}

[Serializable]
public class SupportData
{
    public int node;
    public bool ux;
    public bool uy;
    public bool uz;
    public bool rx;
    public bool ry;
    public bool rz;
}

[Serializable]
public class SlabData
{
    public string id;
    public string level;
    public float thickness;
    public List<List<float>> polygon;
    public float qG;
    public float qQ;
}

[Serializable]
public class LevelData
{
    public string id;
    public float elevation;
}

[Serializable]
public class ModelData
{
    public List<NodeData> nodes;
    public List<ElementData> elements;
    public List<SupportData> supports;
    public List<SlabData> slabs;
    public List<LevelData> levels;
    public List<TributaryArea> tributary_areas;
}

public static class ModelDataLoader
{
    /// <summary>Lee el JSON del contrato desde un TextAsset y construye el ModelData.</summary>
    public static ModelData Load(TextAsset asset)
    {
        return JsonUtility.FromJson<ModelData>(asset.text);
    }

    /// <summary>Índice tag -> nodo; falla explícito ante tags duplicados o inexistentes.</summary>
    public static Dictionary<int, NodeData> BuildNodeIndex(ModelData model)
    {
        var idx = new Dictionary<int, NodeData>();
        foreach (NodeData n in model.nodes)
        {
            if (n == null) continue;
            if (idx.ContainsKey(n.tag))
            {
                throw new Exception($"Nodo tag duplicado: {n.tag}");
            }
            idx.Add(n.tag, n);
        }
        return idx;
    }
}