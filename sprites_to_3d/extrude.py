"""Transforma um cutout RGBA (silhueta de sprite) em uma malha 2.5D texturizada
(extrusao tipo 'recorte de papelao') e exporta como GLB."""

from pathlib import Path

import cv2
import numpy as np
import trimesh
from shapely.geometry import Polygon
from PIL import Image


def _contours_to_polygon(alpha: np.ndarray, simplify_tolerance: float) -> Polygon | None:
    """Extrai o contorno externo + furos do canal alfa e monta um shapely Polygon."""
    binary = (alpha > 127).astype(np.uint8) * 255
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if not contours or hierarchy is None:
        return None

    hierarchy = hierarchy[0]
    outer_idx = None
    outer_area = -1
    for i, h in enumerate(hierarchy):
        if h[3] == -1:  # sem pai => contorno externo
            area = cv2.contourArea(contours[i])
            if area > outer_area:
                outer_area = area
                outer_idx = i

    if outer_idx is None or outer_area < 4:
        return None

    def simplify(cnt):
        eps = max(simplify_tolerance, 0.1)
        approx = cv2.approxPolyDP(cnt, eps, True)
        return approx.reshape(-1, 2)

    exterior = simplify(contours[outer_idx])
    if len(exterior) < 3:
        return None

    holes = []
    for i, h in enumerate(hierarchy):
        if h[3] == outer_idx and cv2.contourArea(contours[i]) > 12:
            hole_pts = simplify(contours[i])
            if len(hole_pts) >= 3:
                holes.append(hole_pts)

    try:
        poly = Polygon(exterior, holes=holes)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty or poly.area < 1:
            return None
        if poly.geom_type == "MultiPolygon":
            poly = max(poly.geoms, key=lambda g: g.area)
        return poly
    except Exception:
        return None


def _build_uv(vertices: np.ndarray, img_w: int, img_h: int) -> np.ndarray:
    """UV a partir das coordenadas XY (em pixels da imagem original) dos vertices.
    Origem da imagem e' canto superior-esquerdo; v invertido para a convencao de UV."""
    u = vertices[:, 0] / img_w
    v = 1.0 - (vertices[:, 1] / img_h)
    return np.stack([u, v], axis=1)


def cutout_to_mesh(
    rgba: np.ndarray,
    thickness_frac: float,
    world_units_per_pixel: float,
    simplify_tolerance: float,
) -> trimesh.Trimesh | None:
    """Converte um cutout RGBA (numpy HxWx4) em uma malha 2.5D extrudada e texturizada."""
    h, w = rgba.shape[:2]
    alpha = rgba[:, :, 3]

    polygon = _contours_to_polygon(alpha, simplify_tolerance)
    if polygon is None:
        return None

    thickness_px = max(thickness_frac * h, 2.0)

    mesh = trimesh.creation.extrude_polygon(polygon, height=thickness_px)

    # extrude_polygon gera vertices com Z em [0, thickness_px] e XY no espaco do
    # polygon (pixels, origem no canto superior-esquerdo da imagem, Y para baixo
    # na imagem mas mantido como eixo "Y" do polygon aqui).
    verts = mesh.vertices
    uv = _build_uv(verts, w, h)

    image = Image.fromarray(rgba, mode="RGBA")
    material = trimesh.visual.material.PBRMaterial(
        baseColorTexture=image,
        baseColorFactor=[255, 255, 255, 255],
        metallicFactor=0.0,
        roughnessFactor=1.0,
    )
    mesh.visual = trimesh.visual.TextureVisuals(uv=uv, material=material)

    # Centraliza X no centro do sprite, ancora Z=0 na base (pe/chao) e Y crescendo
    # para cima (inverte o Y de imagem, que crescia para baixo).
    verts = mesh.vertices.copy()
    verts[:, 0] -= w / 2.0
    verts[:, 1] = (h - verts[:, 1]) - 0  # inverte Y; base da imagem (y=h) -> 0
    verts[:, 2] -= thickness_px / 2.0
    mesh.vertices = verts * world_units_per_pixel

    return mesh


def export_glb(mesh: trimesh.Trimesh, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(out_path), file_type="glb")
