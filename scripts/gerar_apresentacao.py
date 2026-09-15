"""Gera o PDF da apresentação Marp a partir do Markdown em docs/."""

from __future__ import annotations

import shutil
import subprocess
import sys
import os
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "docs" / "apresentacao.md"
SAIDA = RAIZ / "docs" / "apresentacao.pdf"


def main() -> int:
    npx = shutil.which("npx")
    if npx is None:
        print("Erro: npx não encontrado. Instale Node.js para usar o Marp.", file=sys.stderr)
        return 1

    comando = [
        npx,
        "--yes",
        "@marp-team/marp-cli",
        str(ENTRADA),
        "--pdf",
        "--allow-local-files",
        "-o",
        str(SAIDA),
    ]
    ambiente = os.environ.copy()
    if "CHROME_PATH" not in ambiente:
        navegadores = sorted(Path.home().glob(".cache/ms-playwright/**/chrome"))
        if navegadores:
            ambiente["CHROME_PATH"] = str(navegadores[-1])
    subprocess.run(comando, cwd=RAIZ, check=True, env=ambiente)
    print(f"Apresentação gerada em {SAIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())