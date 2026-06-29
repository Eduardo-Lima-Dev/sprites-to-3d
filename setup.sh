#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r sprites_to_3d/requirements.txt

echo
if command -v assimp >/dev/null 2>&1; then
  echo "Conversor FBX encontrado: assimp ($(command -v assimp))"
elif command -v blender >/dev/null 2>&1; then
  echo "Conversor FBX encontrado: blender ($(command -v blender))"
else
  echo "AVISO: nenhum conversor FBX encontrado."
  echo "Para exportar FBX, instale um destes pacotes:"
  echo "  sudo pacman -S assimp     # leve, recomendado"
  echo "  sudo pacman -S blender    # mais pesado, mais fiel"
fi

echo
echo "Setup concluido. Para usar:"
echo "  source .venv/bin/activate"
echo "  python sprites_to_3d/run.py --only character --no-fbx"
