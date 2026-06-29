# Sprites 2D → Modelos 3D (extrusão 2.5D)

Script que transforma sprite sheets 2D (PNG) em modelos 3D simples, no estilo
"recorte de papelão" (cardboard cutout / Paper Mario): cada sprite é recortado da
folha, vira uma silhueta 2D e é extrudado com uma pequena espessura, gerando uma
malha 3D texturizada de verdade (não é um plano/billboard).

## TL;DR — ver as animações agora

O pipeline já roda e o resultado já está gerado em `out/`. Só falta o servidor
local pra ver no navegador (se já estiver rodando, os comandos abaixo não fazem
mal nenhum, só confirmam):

```bash
cd "/home/eduardo/Documentos/Projetos/Modelagem 3D/out"
python3 -m http.server 8743 --bind 127.0.0.1 &
```

Depois abra no navegador:

| Rota                                                          | O que mostra |
|----------------------------------------------------------------|--------------|
| `http://127.0.0.1:8743/preview/character_demo.html`           | **Demo das animações** — setas ◀▶ trocam personagem/NPC/item, teclado troca de pose, itens giram/flutuam sozinhos |
| `http://127.0.0.1:8743/preview/index.html`                     | Galeria com todos os 42 modelos `.glb` (estático, um por vez, orbitável) |

Se a porta 8743 já estiver em uso (servidor anterior ainda rodando), pule o
comando acima e abra as rotas direto — provavelmente já está no ar.

## Estrutura do projeto

```
Assets/                  # folhas de sprite originais (entrada, não tocar)
sprites_to_3d/           # código do pipeline
  config.py                # mapa folha -> categoria + parâmetros (tolerância, espessura etc.)
  segment.py               # remove o fundo e recorta cada sprite da folha
  extrude.py                # transforma cada recorte numa malha 3D (.glb)
  to_fbx.py                 # converte .glb final em .fbx
  run.py                     # script principal (CLI) que roda tudo
  requirements.txt
setup.sh                 # cria o ambiente Python e instala as dependências
unity/
  PoseSwitcher.cs           # alterna poses de um sujeito (personagem ou NPC) na Unity
  ItemAnimator.cs           # gira + flutua um item (moeda, bola etc.) na Unity
out/                      # tudo que o script gera (pode apagar e re-rodar à vontade)
  cutouts/<categoria>/*.png   # sprites recortados, fundo removido (conferência visual)
  glb/<categoria>/*.glb        # modelos 3D intermediários (abrem em Blender, three.js etc.)
  fbx/<categoria>/*.fbx        # modelos 3D finais — é isto que vai pra Unity
  preview/index.html           # galeria HTML com todos os modelos (visualizador 3D)
  preview/character_demo.html  # demo interativa: troca de pose / animação de itens
  manifest.json                 # lista de tudo que foi gerado, com os caminhos de cada arquivo
```

### Categorias e o que cada folha virou

| Folha (`Assets/...`)        | Categoria   | Convertida? |
|------------------------------|-------------|:-----------:|
| `...22_36_31 (1).png`        | `character` | ✅ (9 poses do personagem principal) |
| `...22_36_31 (2).png`        | `items`     | ✅ (13 itens/coletáveis) |
| `...22_36_32 (3).png`        | `npcs`      | ✅ (12 — NPCs + pedrinhas/fragmentos soltos do buraco) |
| `...22_36_32 (4).png`        | `props`     | ✅ (8 cenário/objetos) |
| `...22_36_32 (5).png`        | `ui`        | ❌ pulada de propósito (é HUD/interface, não faz sentido em 3D) |

O mapeamento fica em [`sprites_to_3d/config.py`](sprites_to_3d/config.py) — se adicionar
novas folhas, é só incluir o nome do arquivo ali.

### Os "sujeitos" com pose (personagem e NPCs)

Alguns sprites são poses diferentes do **mesmo personagem/NPC** — esses formam um
"sujeito" que pode trocar de pose (ver seção de animação abaixo). Isso é definido
em `SUBJECTS` no [`sprites_to_3d/config.py`](sprites_to_3d/config.py):

| Sujeito     | Categoria | Poses (`out/fbx/<categoria>/`)                                                                       |
|-------------|-----------|-------------------------------------------------------------------------------------------------------|
| Personagem  | `character` | `idle_front`, `profile_left`, `profile_right`, `back`, `run`, `attack_slingshot`, `crouch`, `hurt` (+ `portrait`, só retrato pra UI) |
| Senhor da vassoura | `npcs` | `old_man_idle`, `old_man_walk`                                                                  |
| Mulher      | `npcs`    | `woman_idle` (só uma pose, não alterna)                                                              |
| Cachorro    | `npcs`    | `dog_idle`, `dog_bark`                                                                                |

O resto de `npcs` (`pothole` = buraco no asfalto, e os fragmentos pequenos
`npcs_03/04/05/08/09/10` = pedrinhas/gravetos soltos) e todos os 13 `items`
(`coin_1`, `money_small`, `piggy_bank`, `slingshot`, `soccer_ball` etc., nomeados
em `POSE_NAMES["items"]`) são objetos avulsos, sem pose alternativa.

## Como usar

### 1. Primeira vez: criar o ambiente

```bash
bash setup.sh
```

Isso cria um `.venv` com tudo que o script precisa (numpy, opencv, trimesh, shapely)
e confere se o conversor de FBX (`assimp`) está instalado no sistema.

### 2. Rodar o pipeline

```bash
source .venv/bin/activate

# tudo (gera cutouts + glb + fbx de todas as categorias)
python sprites_to_3d/run.py

# só uma categoria (bom pra testar/ajustar antes de rodar tudo)
python sprites_to_3d/run.py --only character

# parar na etapa do .glb, sem gerar .fbx (mais rápido, útil pra debugar)
python sprites_to_3d/run.py --no-fbx
```

Cada execução sobrescreve a pasta `out/`. Pode apagar `out/` e rodar de novo quando quiser.

### 3. Ver o resultado sem precisar da Unity

```bash
cd out && python3 -m http.server 8743
```

Depois abra no navegador:

- `http://127.0.0.1:8743/preview/index.html` — galeria com **todos** os modelos
  `.glb` (arrastar = orbitar, scroll = zoom). Útil pra conferir rapidamente se
  algum sprite saiu cortado errado antes de levar pra Unity.
- `http://127.0.0.1:8743/preview/character_demo.html` — demo **interativa** das
  animações (troca de pose do personagem/NPCs, rotação dos itens), ver seção
  abaixo. Mostra exatamente o que os scripts da Unity fazem, sem precisar abrir
  a Unity.

## Como importar na Unity

1. Copie a pasta `out/fbx/` (ou só as subpastas/categorias que quiser) para dentro de
   `Assets/` do seu projeto Unity — por exemplo `Assets/Models/`.
2. A Unity importa o `.fbx` automaticamente. Cada arquivo já vem com:
   - a malha 3D (silhueta extrudada);
   - a textura do sprite aplicada como material (embutida no próprio `.fbx`);
   - origem (pivot) centrada na base do sprite, então ao arrastar pra cena ele já
     encosta no chão (Y = 0) em vez de ficar enterrado ou flutuando.
3. Arraste o `.fbx` da janela **Project** pra dentro da **Scene** ou da **Hierarchy**.
4. Se a textura não vier aplicada automaticamente (raro, mas pode acontecer
   dependendo da versão da Unity), abra o material gerado junto do `.fbx` e
   confira se o slot **Albedo/Base Map** está com a textura do próprio sprite —
   ela fica embutida no arquivo, a Unity normalmente extrai sozinha.
5. Escala: os modelos usam 1 unidade Unity ≈ 100 pixels do sprite original
   (personagem com ~420px de altura vira ~4.2 unidades — do tamanho de uma pessoa).
   Ajuste o `Scale` do objeto na Unity se quiser outro tamanho.

Como é uma extrusão 2.5D, o modelo fica **perfeito visto de frente/trás** e
**uma "placa" fina visto de lado** — isso é esperado para esse estilo (tipo Paper
Mario), não é um defeito.

## Animação

Nenhum modelo tem esqueleto/ossos — cada um é uma silhueta sólida e rígida (um
"boneco de papelão"). Por isso a animação é de dois tipos bem simples:

- **Personagem e NPCs com pose**: troca instantânea entre modelos diferentes
  (mesmo princípio de jogos 2D trocando sprite a cada frame, só que aqui cada
  "frame" é um modelo 3D inteiro). Não interpola, não dobra membro.
- **Itens**: o objeto é único, então "animar" é só girar/flutuar o objeto
  inteiro (moeda rodando, bola quicando etc.).

### Personagem e NPCs — troca de pose (`unity/PoseSwitcher.cs`)

Um único script genérico serve pra qualquer sujeito da tabela acima (personagem,
senhor, mulher, cachorro) — só muda quantas poses cada um tem:

1. Na Hierarchy, crie um GameObject vazio com o nome do sujeito (ex.: `Character`,
   `OldMan`, `Dog`; a `Woman` não precisa, já que ela só tem 1 pose).
2. Importe e arraste os FBX das poses **daquele sujeito** (ver tabela acima) como
   filhos dele, todos na posição local `(0, 0, 0)`.
3. Adicione o script `PoseSwitcher.cs` ao GameObject.
4. No Inspector, em **Poses**, crie um slot por pose: `Name` = nome do arquivo
   sem `.fbx` (ex. `run`, `old_man_walk`, `dog_bark`) e `Target` = o filho
   correspondente.
5. Em **Idle Pose Name**, ponha a pose padrão (`idle_front`, `old_man_idle`,
   `dog_idle`, `woman_idle`).
6. (Opcional, pra testar sem escrever outro script) em **Debug Key Bindings**,
   associe teclas a poses — segurar a tecla mostra a pose, soltar volta pro
   idle. Sugestão pro personagem: W/↑→`run`, A→`profile_left`, D→`profile_right`,
   S→`back`, Espaço→`attack_slingshot`, C→`crouch`, X→`hurt`. Pro cachorro:
   Espaço→`dog_bark`. Pro senhor: W/↑→`old_man_walk`.
7. Do seu script de gameplay/IA: `GetComponent<PoseSwitcher>().SetPose("run")`.

### Itens — giro e flutuação (`unity/ItemAnimator.cs`)

Mais simples ainda: adicione o script direto no GameObject do FBX do item na
cena (qualquer um dos 13 em `out/fbx/items/`). Ele já gira em torno do eixo Y e
flutua verticalmente sozinho — ajuste `Rotate Speed`, `Bob Amplitude` e
`Bob Speed` no Inspector se quiser variar entre itens (moeda mais rápida,
cofrinho quase parado etc.). Não precisa de mais nenhum FBX/pose extra.

### Testar tudo isso sem abrir a Unity

A demo `out/preview/character_demo.html` (ver seção "Ver o resultado sem
precisar da Unity") replica os dois scripts acima no navegador: aba
**Personagens/NPCs** com setas pra trocar de sujeito e teclado pra trocar de
pose; aba **Itens** com setas pra trocar de item, já girando/flutuando
automaticamente.

**Quer um boneco articulado de verdade** (membros se dobrando, ciclo de
caminhada suave)? Isso exige separar cada pose em cabeça/tronco/braços/pernas
com juntas — as poses atuais são silhuetas de corpo inteiro, então recortar os
membros seria trabalho manual adicional. Nesse caso, o pacote **2D Animation**
da própria Unity (ou Spine2D) é a ferramenta certa, feita exatamente pra esse
tipo de rig "cutout".

## Ajustando a qualidade do recorte

Se algum sprite sair com pedaço faltando, fundo sobrando, ou partes que deveriam
ser uma peça só saindo separadas, ajuste os parâmetros da categoria em
[`sprites_to_3d/config.py`](sprites_to_3d/config.py):

- `bg_tolerance`: o quão parecido com o fundo um pixel precisa ser pra ser removido.
  Aumentar remove mais fundo (mas pode comer parte do sprite); diminuir é mais
  conservador (mas pode deixar resíduo de fundo).
- `min_area`: tamanho mínimo (em pixels²) pra algo ser considerado um sprite válido.
  Aumentar descarta fragmentos pequenos (ex.: pedrinhas soltas).
- `merge_kernel`: o quanto "juntar" partes próximas do mesmo sprite antes de separar
  por objeto. Aumentar evita que um sprite quebre em vários pedaços; diminuir evita
  juntar sprites que deveriam ficar separados.
- `thickness_frac`: espessura da extrusão, proporcional à altura do sprite.

Depois de mudar, rode de novo só a categoria afetada (`--only <categoria>`) e
confira em `out/cutouts/<categoria>/` ou na galeria HTML.
