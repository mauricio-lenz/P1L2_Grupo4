using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// Genera la escena principal del viewer (Assets/Scenes/Main.unity) en modo batch:
/// cámara navegable, luz, y GameObject App con ModelBuilder apuntando al contrato JSON.
/// Ejecutar:
///   Unity -batchmode -quit -projectPath unity -executeMethod SceneWizard.BuildMain
/// </summary>
public static class SceneWizard
{
    public static void BuildMain()
    {
        string scenesDir = "Assets/Scenes";
        if (!AssetDatabase.IsValidFolder(scenesDir))
        {
            Directory.CreateDirectory(Path.Combine(
                Directory.GetCurrentDirectory(), scenesDir));
            AssetDatabase.Refresh();
        }

        var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,
                                                NewSceneMode.Single);

        Camera cam = Object.FindObjectOfType<Camera>();
        if (cam != null)
        {
            cam.gameObject.name = "Main Camera";
            cam.transform.position = new Vector3(30f, 45f, 95f);
            cam.transform.LookAt(new Vector3(30f, 4f, 45f));
            cam.gameObject.AddComponent<FreeFlyCamera>();
        }

        var lightGo = new GameObject("Directional Light");
        var light = lightGo.AddComponent<Light>();
        light.type = LightType.Directional;
        lightGo.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

        var app = new GameObject("App");
        var mb = app.AddComponent<ModelBuilder>();
        var asset = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/Data/model_data.json");
        if (asset == null)
        {
            Debug.LogError("SceneWizard: Assets/Data/model_data.json no encontrado. " +
                           "Copia data/model_data.json a unity/Assets/Data/.");
        }
        else
        {
            SerializedObject so = new SerializedObject(mb);
            so.FindProperty("modelJson").objectReferenceValue = asset;
            so.ApplyModifiedProperties();
        }
        app.AddComponent<ViewControls>();
        app.AddComponent<TributaryInspector>();

        EditorSceneManager.SaveScene(scene, scenesDir + "/Main.unity");
        Debug.Log("SceneWizard: Assets/Scenes/Main.unity guardada.");
    }
}