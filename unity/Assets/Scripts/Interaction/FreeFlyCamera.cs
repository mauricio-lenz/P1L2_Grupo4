using UnityEngine;

/// <summary>
/// Cámara de navegación simple para QA del modelo (física de vuelo).
/// WASD/Ejes laterales; Shift acelera; Q/E sube/baja; clic derecho para rotar.
/// </summary>
public class FreeFlyCamera : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 20f;
    [SerializeField] private float rotateSpeed = 90f;

    private void Update()
    {
        float boost = Input.GetKey(KeyCode.LeftShift) ? 3f : 1f;
        float speed = moveSpeed * boost;

        Vector3 forward = transform.forward;
        Vector3 right = transform.right;
        Vector3 flatForward = Vector3.ProjectOnPlane(forward, Vector3.up).normalized;
        Vector3 flatRight = Vector3.ProjectOnPlane(right, Vector3.up).normalized;

        Vector3 move = Vector3.zero;
        if (Input.GetKey(KeyCode.W)) move += flatForward;
        if (Input.GetKey(KeyCode.S)) move -= flatForward;
        if (Input.GetKey(KeyCode.D)) move += flatRight;
        if (Input.GetKey(KeyCode.A)) move -= flatRight;
        if (Input.GetKey(KeyCode.E)) move += Vector3.up;
        if (Input.GetKey(KeyCode.Q)) move -= Vector3.up;
        transform.position += move * speed * Time.deltaTime;

        if (Input.GetMouseButton(1))
        {
            float yaw = Input.GetAxis("Mouse X") * rotateSpeed * Time.deltaTime;
            float pitch = -Input.GetAxis("Mouse Y") * rotateSpeed * Time.deltaTime;
            transform.Rotate(Vector3.up, yaw, Space.World);
            transform.Rotate(transform.right, pitch, Space.World);
        }
    }
}