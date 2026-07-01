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

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or default


def _ask_yes_no(prompt: str, default_yes: bool = True) -> bool:
    suffix = "S/n" if default_yes else "s/N"
    answer = input(f"{prompt} ({suffix}): ").strip().lower()
    if not answer:
        return default_yes
    return answer.startswith("s")


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else (PROJECT_ROOT / path)


def interactive_args() -> argparse.Namespace:
    """Pergunta ao usuario o que processar, ao inves de exigir flags de linha de
    comando -- usado quando o script e' chamado sem nenhum argumento, pra facilitar
    rodar o pipeline pra um novo lote de imagens sem precisar lembrar a sintaxe."""
    print("=== sprites_to_3d ===")
    print("O que voce quer converter?")
    print("  1) Os assets padrao ja mapeados em config.py (character/items/npcs/props)")
    print("  2) Uma pasta nova de imagens (categoria customizada)")
    choice = _ask("Escolha 1 ou 2", "2")

    args = argparse.Namespace(
        input=str(ASSETS_DIR), output=str(OUT_DIR),
        only=None, no_fbx=False, category=None, name_prefix="item",
    )

    if choice == "1":
        only = _ask("Processar so uma categoria? (Enter = todas) [character/items/npcs/props]")
        args.only = only or None
        args.output = str(_resolve(_ask("Pasta de saida", "out")))
    else:
        input_dir = _ask("Pasta com as imagens (caminho a partir da raiz do projeto)", "Assets/Sprites")
        resolved_input = _resolve(input_dir)
        while not resolved_input.is_dir():
            print(f"  Pasta nao encontrada: {resolved_input}")
            input_dir = _ask("Pasta com as imagens (caminho a partir da raiz do projeto)")
            resolved_input = _resolve(input_dir)
        args.input = str(resolved_input)

        category = _ask("Nome da categoria (ex: houses, furniture, vehicles)")
        while not category:
            category = _ask("Nome da categoria (obrigatorio)")
        args.category = category
        args.name_prefix = _ask("Prefixo para nomear os arquivos gerados", category)
        args.output = str(_resolve(_ask("Pasta de saida (caminho a partir da raiz do projeto)", category.capitalize())))

    gerar_fbx = _ask_yes_no("Gerar FBX com texturas (alem do GLB)?", True)
    args.no_fbx = not gerar_fbx

    print("\nResumo:")
    print(f"  entrada:   {args.input}")
    print(f"  saida:     {args.output}")
    if args.category:
        print(f"  categoria: {args.category}  (prefixo: {args.name_prefix})")
    if args.only:
        print(f"  somente:   {args.only}")
    print(f"  gerar fbx: {'sim' if not args.no_fbx else 'nao'}\n")

    if not _ask_yes_no("Continuar?", True):
        print("Cancelado.")
        sys.exit(0)

    return args


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
        default="item",
        help="Prefixo usado para nomear cada folha em modo --category (ex: house -> house_01, house_02, ...)",
    )
    args = parser.parse_args() if len(sys.argv) > 1 else interactive_args()

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
        if input_dir.is_file():
            sheet_paths = [input_dir]
        else:
            sheet_paths = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in image_exts)
        # com uma unica folha nao ha' o que numerar -- usa o prefixo tal qual foi digitado
        if len(sheet_paths) == 1:
            sheets = [(sheet_paths[0], args.category, args.name_prefix)]
        else:
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
        # em modo --category o usuario escolheu explicitamente o que converter;
        # o filtro CONVERTIBLE_CATEGORIES so se aplica ao mapa fixo SHEET_CATEGORY
        if not args.category and category not in CONVERTIBLE_CATEGORIES:
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
            if name_prefix and len(cutouts) == 1:
                # folha com um unico sprite: o prefixo digitado pelo usuario ja'
                # e' o nome final -- evita cair no POSE_NAMES por indice (ex.:
                # indice 0 de "character" e' "idle_front", que nao se aplica aqui)
                name = name_prefix
            else:
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
