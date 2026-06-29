"""Remove o fundo (xadrez/branco pintado em RGB) de uma folha de sprites e recorta
cada sprite individual como PNG RGBA."""

from pathlib import Path

import cv2
import numpy as np


def _background_mask(bgr: np.ndarray, tolerance: int) -> np.ndarray:
    """Mascara booleana (True = fundo) a partir de flood fill nas bordas.

    O fundo das folhas e' um xadrez cinza claro/branco ou branco solido. Usa-se
    FLOODFILL_FIXED_RANGE (compara sempre contra a cor da semente, nao do vizinho)
    para nao "vazar" por gradientes suaves de objetos metalicos/sombreados -- modo
    floating-range (default do OpenCV) deixaria o flood fill caminhar por um brilho
    especular ate dentro de um objeto. Varias sementes ao longo das bordas cobrem as
    duas tonalidades do xadrez.
    """
    h, w = bgr.shape[:2]
    flood_mask = np.zeros((h + 2, w + 2), np.uint8)
    filled = bgr.copy()

    border_points = set()
    for frac in (0.0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0):
        border_points.add((int((w - 1) * frac), 0))
        border_points.add((int((w - 1) * frac), h - 1))
        border_points.add((0, int((h - 1) * frac)))
        border_points.add((w - 1, int((h - 1) * frac)))

    flags = 4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8)
    for sx, sy in border_points:
        if flood_mask[sy + 1, sx + 1] == 0:
            cv2.floodFill(
                filled,
                flood_mask,
                (sx, sy),
                0,
                loDiff=(tolerance,) * 3,
                upDiff=(tolerance,) * 3,
                flags=flags,
            )

    bg = flood_mask[1:-1, 1:-1] > 0
    return _grow_fringe(bg, bgr, max_steps=40)


def _grow_fringe(bg: np.ndarray, bgr: np.ndarray, max_steps: int) -> np.ndarray:
    """Cresce o fundo 1px por vez, por ate' `max_steps` iteracoes, absorvendo
    franjas de anti-aliasing e bolsoes de fundo cercados pela silhueta (ex.: o
    vao entre as pernas numa pose agachada) que o flood fill nao alcanca --
    nem com tolerancia alta, porque sao pixels sem nenhum caminho de cor
    parecida até a borda da imagem. O crescimento e' limitado a poucos pixels
    por vez: ao contrario de um flood fill solto, nao "viaja" indefinidamente
    por gradientes longos pra dentro de objetos (o que comia brilhos de
    objetos metalicos antes do FLOODFILL_FIXED_RANGE).
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    bg_like = (hsv[:, :, 1] < 20) & (hsv[:, :, 2] > 140)

    kernel3 = np.ones((3, 3), np.uint8)
    for _ in range(max_steps):
        ring = cv2.dilate(bg.astype(np.uint8), kernel3) > 0
        ring &= ~bg
        new_bg_px = ring & bg_like
        if not new_bg_px.any():
            break
        bg = bg | new_bg_px

    return bg


def _clean_mask(fg_mask: np.ndarray, erode_px: int) -> np.ndarray:
    fg = fg_mask.astype(np.uint8) * 255
    kernel3 = np.ones((3, 3), np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel3)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    if erode_px > 0:
        fg = cv2.erode(fg, kernel3, iterations=erode_px)
    return fg


def segment_sheet(image_path: Path, params: dict) -> list[np.ndarray]:
    """Carrega uma folha de sprites e retorna lista de cutouts RGBA, um por sprite
    detectado, ordenados em leitura (topo->baixo, esquerda->direita)."""
    bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"Nao foi possivel ler a imagem: {image_path}")

    bg = _background_mask(bgr, params["bg_tolerance"])
    fg_mask = _clean_mask(~bg, params["erode_px"])

    merge_kernel = params["merge_kernel"]
    merge = cv2.dilate(fg_mask, np.ones((merge_kernel, merge_kernel), np.uint8))

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(merge, connectivity=8)

    items = []
    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]
        if area < params["min_area"]:
            continue
        x, y, w, h = stats[label, cv2.CC_STAT_LEFT:cv2.CC_STAT_LEFT + 4]

        component_mask = labels[y:y + h, x:x + w] == label
        local_alpha = np.where(component_mask, fg_mask[y:y + h, x:x + w], 0)

        if not local_alpha.any():
            continue

        bgr_crop = bgr[y:y + h, x:x + w]
        rgba = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGBA)
        rgba[:, :, 3] = local_alpha

        ys, xs = np.where(local_alpha > 0)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        cropped = rgba[y0:y1, x0:x1]
        items.append((y + y0, x + x0, cropped))

    # agrupa por proximidade vertical (linhas da folha) e ordena por x dentro da linha
    items.sort(key=lambda it: (round(it[0] / 80), it[1]))

    return [img for _, _, img in items]
