using UnityEngine;

/// <summary>
/// Anima qualquer item rigido (moeda, bola, cofrinho etc.) com rotacao
/// continua + flutuacao vertical leve. Os itens nao tem esqueleto/poses --
/// sao uma unica malha solida (recorte extrudado) -- entao a "animacao" e'
/// so transformar o objeto inteiro. Funciona em qualquer FBX de item sem
/// configuracao extra; ajuste as velocidades/amplitude no Inspector se quiser
/// variar entre itens (ex.: moeda gira mais rapido, cofrinho quase nao flutua).
///
/// Setup: adicione este script direto no GameObject do FBX do item na cena.
/// </summary>
public class ItemAnimator : MonoBehaviour
{
    [Header("Rotacao (graus/segundo, eixo Y)")]
    public float rotateSpeed = 90f;

    [Header("Flutuacao vertical")]
    public float bobAmplitude = 0.1f;
    public float bobSpeed = 2f;

    Vector3 _basePosition;

    void Start()
    {
        _basePosition = transform.localPosition;
    }

    void Update()
    {
        transform.Rotate(Vector3.up, rotateSpeed * Time.deltaTime, Space.Self);

        float y = Mathf.Sin(Time.time * bobSpeed) * bobAmplitude;
        transform.localPosition = _basePosition + new Vector3(0f, y, 0f);
    }
}
