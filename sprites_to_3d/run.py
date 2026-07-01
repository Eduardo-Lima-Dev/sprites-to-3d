"""CLI que orquestra o pipeline: segment -> extrude -> (opcional) to_fbx."""

import argparse
import json
import shutil
import sys
from pathlib import Path

import cv2

from config import ASSETS_DIR, OUT_DIR, SHEET_CATEGORY, CONVERTIBLE_CATEGORIES, POSE_NAMES, get_params
from segment import segment_sheet
from extrude import cutout_to_mesh, export_glb
from to_fbx import convert_glb_to_fbx, find_converter


def main():
    parser = argparse.ArgumentParser(description="Converte sprite sheets 2D em modelos 3D 2.5D")
    parser.add_argument("--input", default=str(ASSETS_DIR), help="Pasta com as folhas de sprite")
    parser.add_argument("--output", default=str(OUT_DIR), help="Pasta de saida")
    parser.add_argument("--only", default=None, help="Processar apenas esta categoria (ex: character)")
    parser.add_argument("--no-fbx", action="store_true", help="Parar apos gerar os GLB, sem converter para FBX")
    parser.add_argument(
        "--category",
        default=None,
        help=(
            "Ignora o mapa fixo SHEET_CATEGORY e processa toda imagem encontrada "
            "diretamente em --input, atribuindo essa categoria a todas (ex: houses)"
        ),
    )
    parser.add_argument(
        "--name-prefix",
        default="house",
        help="Prefixo usado para nomear cada folha em modo --category (ex: house -> house_01, house_02, ...)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    cutouts_dir = output_dir / "cutouts"
    glb_dir = output_dir / "glb"
    fbx_dir = output_dir / "fbx"

    if not args.no_fbx and find_converter() is None:
        print("AVISO: nenhum conversor FBX encontrado (assimp/blender).")
        print("Instale com: sudo pacman -S assimp")
        print("Continuando apenas até a etapa GLB.\n")
        args.no_fbx = True

    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    if args.category:
        image_exts = {".png", ".jpg", ".jpeg"}
        sheet_paths = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in image_exts)
        sheets = [
            (sheet_path, args.category, f"{args.name_prefix}_{idx:02d}")
            for idx, sheet_path in enumerate(sheet_paths, start=1)
        ]
    else:
        sheets = [
            (input_dir / filename, category, None)
            for filename, category in SHEET_CATEGORY.items()
        ]

    for sheet_path, category, name_prefix in sheets:
        if category not in CONVERTIBLE_CATEGORIES:
            continue
        if args.only and category != args.only:
            continue

        if not sheet_path.exists():
            print(f"[{category}] arquivo nao encontrado, pulando: {sheet_path}")
            continue

        print(f"[{category}] segmentando {sheet_path.name} ...")
        params = get_params(category)
        cutouts = segment_sheet(sheet_path, params)
        print(f"[{category}] {len(cutouts)} sprite(s) detectado(s)")

        manifest.setdefault(category, [])
        cat_cutout_dir = cutouts_dir / category
        cat_cutout_dir.mkdir(parents=True, exist_ok=True)

        for i, rgba in enumerate(cutouts):
            pose_name = POSE_NAMES.get(category, {}).get(i, f"{category}_{i:02d}")
            name = f"{name_prefix}_{pose_name}" if name_prefix else pose_name

            cutout_path = cat_cutout_dir / f"{name}.png"
            cv2.imwrite(str(cutout_path), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))

            mesh = cutout_to_mesh(
                rgba,
                thickness_frac=params["thickness_frac"],
                world_units_per_pixel=params["world_units_per_pixel"],
                simplify_tolerance=params["simplify_tolerance"],
            )
            if mesh is None:
                print(f"  [{name}] contorno vazio/invalido, pulando")
                continue

            glb_path = glb_dir / category / f"{name}.glb"
            export_glb(mesh, glb_path)

            entry = {
                "name": name,
                "category": category,
                "cutout_png": str(cutout_path.relative_to(output_dir)),
                "glb": str(glb_path.relative_to(output_dir)),
                "width_px": int(rgba.shape[1]),
                "height_px": int(rgba.shape[0]),
            }

            if not args.no_fbx:
                fbx_path = fbx_dir / category / f"{name}.fbx"
                ok = convert_glb_to_fbx(glb_path, fbx_path)
                if ok:
                    entry["fbx"] = str(fbx_path.relative_to(output_dir))
                    tex_dst = fbx_path.parent / "Textures" / cutout_path.name
                    tex_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(cutout_path, tex_dst)
                else:
                    print(f"  [{name}] conversao para FBX falhou")

            manifest[category].append(entry)
            print(f"  [{name}] ok -> {entry.get('fbx', entry['glb'])}")

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nManifest escrito em {manifest_path}")


if __name__ == "__main__":
    sys.exit(main())
