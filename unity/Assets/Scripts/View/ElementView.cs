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

    private float radius;

    public void Initialize(int elementTag, int nodeI, int nodeJ, string kind, float radius)
    {
        ElementTag = elementTag;
        NodeI = nodeI;
        NodeJ = nodeJ;
        Kind = kind;
        this.radius = radius;
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
        transform.position = 0.5f * (a + b);
        transform.rotation = Quaternion.FromToRotation(Vector3.up, d.normalized);
        // El primitive Cylinder de Unity tiene altura 2 por defecto.
        transform.localScale = new Vector3(radius, 0.5f * length, radius);
    }
}