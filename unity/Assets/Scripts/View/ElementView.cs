using UnityEngine;

/// <summary>
/// Visualiza un elemento estructural como cilindro entre sus dos nodos
/// (centrelines), siguiendo el tutorial P1. La línea central se usa para QA de
/// conectividad antes de representar la sección.
/// </summary>
public class ElementView : MonoBehaviour
{
    public int ElementTag { get; private set; }
    public int NodeI { get; private set; }
    public int NodeJ { get; private set; }
    public string Kind { get; private set; }
    public Vector3 LocalX { get; private set; }

    private float width = 0.2f;
    private float depth = 0.2f;

    public void Initialize(int elementTag, int nodeI, int nodeJ, string kind, float radius)
    {
        ElementTag = elementTag;
        NodeI = nodeI;
        NodeJ = nodeJ;
        Kind = kind;
        SetCrossSection(kind, radius);
    }

    /// <summary>Dimensiones de la sección recta (b x h) para el prisma.</summary>
    public void SetCrossSection(string kind, float radius)
    {
        switch (kind)
        {
            case "column": width = 0.4f; depth = 0.4f; break;
            case "wall": width = radius * 0.8f; depth = 2.0f; break;
            default: width = 0.3f; depth = 0.5f; break; // viga
        }
    }

    public void SetLocalX(Vector3 localX)
    {
        LocalX = localX;
    }

    public void SetEndpoints(Vector3 a, Vector3 b)
    {
        Vector3 d = b - a;
        float length = d.magnitude;
        if (length <= 1.0e-8f)
        {
            Debug.LogError($"Element {ElementTag} has zero or near-zero length.");
            return;
        }
        // Prisma rectangular: eje del elemento a lo largo de Y local del cubo.
        transform.position = 0.5f * (a + b);
        transform.rotation = Quaternion.FromToRotation(Vector3.up, d.normalized);
        transform.localScale = new Vector3(width, length, depth);
    }
}