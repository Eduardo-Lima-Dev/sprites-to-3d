"""Converte um GLB (malha + textura embutida) em FBX, usando assimp (preferido)
ou Blender headless como fallback."""

import shutil
import subprocess
from pathlib import Path

_BLENDER_SCRIPT = """
import bpy
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
in_glb, out_fbx = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=in_glb)
bpy.ops.export_scene.fbx(filepath=out_fbx, embed_textures=True, path_mode='COPY')
"""


def find_converter() -> str | None:
    if shutil.which("assimp"):
        return "assimp"
    if shutil.which("blender"):
        return "blender"
    return None


def convert_glb_to_fbx(glb_path: Path, fbx_path: Path) -> bool:
    fbx_path.parent.mkdir(parents=True, exist_ok=True)
    converter = find_converter()

    if converter == "assimp":
        result = subprocess.run(
            ["assimp", "export", str(glb_path), str(fbx_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  [assimp] falhou: {result.stderr.strip()}")
            return False
        return fbx_path.exists()

    if converter == "blender":
        script_path = fbx_path.parent / "_glb_to_fbx_blender.py"
        script_path.write_text(_BLENDER_SCRIPT)
        result = subprocess.run(
            ["blender", "-b", "--python", str(script_path), "--",
             str(glb_path), str(fbx_path)],
            capture_output=True, text=True,
        )
        script_path.unlink(missing_ok=True)
        if result.returncode != 0:
            print(f"  [blender] falhou: {result.stderr.strip()}")
            return False
        return fbx_path.exists()

    print("  Nenhum conversor FBX encontrado (instale 'assimp' ou 'blender').")
    return False
