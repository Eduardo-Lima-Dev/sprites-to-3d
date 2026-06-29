"""Mapa de folhas de sprite -> categoria, e parametros de processamento por categoria."""

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "Assets"
OUT_DIR = Path(__file__).resolve().parent.parent / "out"

# Nome do arquivo (relativo a ASSETS_DIR) -> categoria
SHEET_CATEGORY = {
    "ChatGPT Image 27 de jun. de 2026, 22_36_31 (1).png": "character",
    "ChatGPT Image 27 de jun. de 2026, 22_36_31 (2).png": "items",
    "ChatGPT Image 27 de jun. de 2026, 22_36_32 (3).png": "npcs",
    "ChatGPT Image 27 de jun. de 2026, 22_36_32 (4).png": "props",
    "ChatGPT Image 27 de jun. de 2026, 22_36_32 (5).png": "ui",  # pulada
}

# Categorias que sao efetivamente convertidas para 3D
CONVERTIBLE_CATEGORIES = {"character", "items", "npcs", "props"}

# Nome semantico por indice de sprite dentro da categoria (na ordem de leitura da
# folha: topo->baixo, esquerda->direita). Usado para nomear os arquivos de saida e
# para o script de troca de poses na Unity. Categorias/indices sem entrada aqui
# caem no nome generico "<categoria>_NN".
POSE_NAMES = {
    "character": {
        0: "idle_front",
        1: "profile_left",
        2: "profile_right",
        3: "back",
        4: "run",
        5: "attack_slingshot",
        6: "crouch",
        7: "hurt",
        8: "portrait",
    },
    "npcs": {
        0: "old_man_walk",
        1: "old_man_idle",
        2: "woman_idle",
        6: "dog_idle",
        7: "dog_bark",
        11: "pothole",
    },
    "items": {
        0: "money_small",
        1: "money_medium",
        2: "money_large",
        3: "coin_1",
        4: "coin_5",
        5: "coin_10",
        6: "coxinha",
        7: "sandwich",
        8: "inhaler",
        9: "slingshot",
        10: "soccer_ball",
        11: "rocks",
        12: "piggy_bank",
    },
}

# Agrupa poses por "sujeito" pra troca de pose (Unity PoseSwitcher / demo HTML).
# Cada sujeito tem uma pose "idle" (padrao quando nenhuma tecla/estado especial
# esta ativo) e zero ou mais poses extras. Sujeitos com 1 pose so (ex.: woman)
# nao tem o que alternar, mas entram na lista pra aparecer no seletor.
SUBJECTS = {
    "character": {
        "label": "Personagem principal",
        "category": "character",
        "idle": "idle_front",
        "poses": [
            "idle_front", "profile_left", "profile_right", "back",
            "run", "attack_slingshot", "crouch", "hurt",
        ],
    },
    "old_man": {
        "label": "Senhor da vassoura",
        "category": "npcs",
        "idle": "old_man_idle",
        "poses": ["old_man_idle", "old_man_walk"],
    },
    "woman": {
        "label": "Mulher",
        "category": "npcs",
        "idle": "woman_idle",
        "poses": ["woman_idle"],
    },
    "dog": {
        "label": "Cachorro",
        "category": "npcs",
        "idle": "dog_idle",
        "poses": ["dog_idle", "dog_bark"],
    },
}
SUBJECT_ORDER = ["character", "old_man", "woman", "dog"]

# Parametros default de segmentacao/extrusao, com overrides por categoria
DEFAULTS = {
    "bg_tolerance": 18,       # tolerancia de cor (0-255) para considerar fundo
    "min_area": 600,          # area minima (px^2) de um componente para ser um sprite valido
    "merge_kernel": 9,        # tamanho do kernel de dilatacao usado para unir partes soltas do mesmo sprite
    "erode_px": 1,            # erosao da mascara para remover halo de anti-aliasing
    "thickness_frac": 0.06,   # espessura da extrusao = thickness_frac * altura do sprite (em pixels)
    "world_units_per_pixel": 0.01,  # escala: 1px de sprite = 0.01 unidades de mundo (1254px ~ 12.5u)
    "simplify_tolerance": 1.5,  # tolerancia (px) de simplificacao do contorno (approxPolyDP / shapely)
    "fill_pockets": False,    # preenche bolsoes de fundo cercados pela silhueta (vao entre pernas etc.)
}

CATEGORY_OVERRIDES = {
    "character": {"thickness_frac": 0.05, "merge_kernel": 11, "fill_pockets": True},
    "npcs": {"thickness_frac": 0.05, "merge_kernel": 11, "fill_pockets": True},
    # fill_pockets so no slingshot (indice 9, "Y" vazado entre as duas pontas)
    # -- o resto dos items e' objeto rigido sem vao desse tipo, e correu risco
    # de fragmentar (moeda, sanduiche, cofrinho) quando testado com tudo ligado
    "items": {"thickness_frac": 0.12, "merge_kernel": 7, "fill_pockets": {9}},
    "props": {"thickness_frac": 0.08, "merge_kernel": 7, "min_area": 900},
}


def get_params(category: str) -> dict:
    params = dict(DEFAULTS)
    params.update(CATEGORY_OVERRIDES.get(category, {}))
    return params
