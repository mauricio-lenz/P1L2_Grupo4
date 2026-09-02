using UnityEngine;

/// <summary>
/// Prueba manual del tutorial P1: una viga de 4 m entre (0,0,0) y (4,0,0) que debe
/// verse como un cilindro orientado según la conversión de coordenadas.
/// Si conviven ManualBeamExample y ModelBuilder, desactiva uno (checkbox).
/// </summary>
public class ManualBeamExample : MonoBehaviour
{
    private void Start()
    {
        Vector3 a = CoordinateMap.OsToUnity(0.0f, 0.0f, 0.0f);
        Vector3 b = CoordinateMap.OsToUnity(4.0f, 0.0f, 0.0f);
        GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        go.name = "Element_101";
        ElementView view = go.AddComponent<ElementView>();
        view.Initialize(101, 1, 2, "beam", 0.05f);
        view.SetEndpoints(a, b);
    }
}