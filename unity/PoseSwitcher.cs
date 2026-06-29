using UnityEngine;

/// <summary>
/// Alterna entre os modelos 3D de cada pose de um "sujeito" (personagem, NPC
/// etc.) -- mesmo principio de jogos 2D que trocam o sprite a cada frame, so
/// que aqui cada "frame" e' um modelo 3D inteiro (sem esqueleto, sem
/// interpolacao -- a troca e' instantanea). Generico: funciona pro
/// personagem, pro senhor da vassoura, pro cachorro etc., so muda quantas
/// poses cada um tem.
///
/// Setup:
/// 1. Crie um GameObject vazio (ex.: "Character", "OldMan", "Dog").
/// 2. Arraste cada FBX de pose do sujeito como filho dele, todos em (0,0,0).
/// 3. Adicione este script ao GameObject.
/// 4. Em "Poses", um slot por pose: Name = nome do arquivo sem ".fbx"
///    (ex. "run", "old_man_walk", "dog_bark"), Target = o filho correspondente.
/// 5. Defina "Idle Pose Name" (a pose default, ex. "idle_front", "dog_idle").
/// 6. (Opcional) em "Debug Key Bindings", associe teclas a poses pra testar
///    sem escrever outro script. Soltar a tecla volta pro idle.
/// 7. Do seu script de gameplay/IA: GetComponent<PoseSwitcher>().SetPose("run");
/// </summary>
public class PoseSwitcher : MonoBehaviour
{
    [System.Serializable]
    public class Pose
    {
        public string name;
        public GameObject target;
    }

    [System.Serializable]
    public class KeyBinding
    {
        public KeyCode key;
        public string poseName;
    }

    [Header("Um slot por pose (name = nome do arquivo, sem .fbx)")]
    public Pose[] poses;

    [Header("Pose default (quando nenhuma tecla de debug esta pressionada)")]
    public string idlePoseName = "idle";

    [Header("Debug: tecla segurada = pose; solta = volta pro idle")]
    public bool enableDebugInput = true;
    public KeyBinding[] debugKeyBindings;

    string _current;

    void Start()
    {
        SetPose(idlePoseName);
    }

    void Update()
    {
        if (!enableDebugInput || debugKeyBindings == null) return;

        foreach (var kb in debugKeyBindings)
        {
            if (Input.GetKey(kb.key))
            {
                SetPose(kb.poseName);
                return;
            }
        }
        SetPose(idlePoseName);
    }

    public void SetPose(string poseName)
    {
        if (poses == null || poseName == _current) return;

        foreach (var p in poses)
            p.target?.SetActive(p.name == poseName);

        _current = poseName;
    }
}
